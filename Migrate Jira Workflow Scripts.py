import argparse
import csv
import json
import os
import re
import time
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter, Retry
from requests.auth import HTTPBasicAuth

from environment_config import get_environment

SOURCE_ENV = get_environment("open_groupe_sandbox_source")
TARGET_ENV = get_environment("open_groupe_sandbox_target")
SOURCE_BASE_URL = SOURCE_ENV["jira_base_url"]
SOURCE_USER = SOURCE_ENV["username"]
SOURCE_TOKEN = SOURCE_ENV["user_token"]
TARGET_BASE_URL = TARGET_ENV["jira_base_url"]
TARGET_USER = TARGET_ENV["username"]
TARGET_TOKEN = TARGET_ENV["user_token"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILES_DIR = os.path.join(SCRIPT_DIR, 'Files')
FIELDS_MAPPING_CSV = os.path.join(FILES_DIR, 'Fields Mapping.csv')
WORKFLOW_DEFINITION_LOG_CSV = os.path.join(FILES_DIR, 'Workflow Definitions Checked.csv')
WORKFLOW_CONVERSION_LOG_CSV = os.path.join(FILES_DIR, 'Workflow Conversion Log.csv')
WORKFLOW_UPDATE_PAYLOAD_LOG_CSV = os.path.join(FILES_DIR, 'Workflow Update Payloads.csv')

CUSTOMFIELD_PATTERN = re.compile(r'customfield_(\d+)')
APPKEY_PREFIX = 'com.onresolve'


class JiraClient:
    def __init__(self, base_url, auth):
        self.base_url = base_url.rstrip('/')
        self.auth = auth
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            respect_retry_after_header=True,
            allowed_methods=['GET', 'POST', 'PUT', 'DELETE'],
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def request(self, method, uri, params=None, json_body=None, headers=None):
        url = urljoin(self.base_url + '/', uri.lstrip('/'))
        headers = headers or {'Accept': 'application/json'}
        for attempt in range(8):
            response = self.session.request(
                method,
                url,
                auth=self.auth,
                params=params,
                json=json_body,
                headers=headers,
                timeout=60,
            )
            if response.status_code == 429:
                wait = self._get_retry_after(response)
                wait = wait if wait is not None else min(60, 2 ** attempt)
                print(f'Rate limited on {method} {uri}; sleeping {wait}s then retrying')
                time.sleep(wait)
                continue
            body = None
            try:
                body = response.json()
            except ValueError:
                body = None
            return {
                'ok': response.ok,
                'status_code': response.status_code,
                'body': body,
                'headers': response.headers,
            }
        raise RuntimeError(f'Failed to call {method} {uri} after retries')

    def _get_retry_after(self, response):
        header = response.headers.get('Retry-After')
        if header:
            try:
                return int(header)
            except ValueError:
                pass
        header = response.headers.get('X-RateLimit-Reset')
        if header:
            try:
                reset_ts = datetime.strptime(header, '%Y-%m-%dT%H:%MZ')
                return max(0, (reset_ts - datetime.utcnow()).total_seconds())
            except ValueError:
                pass
        return None

    def get(self, uri, params=None, headers=None):
        return self.request('GET', uri, params=params, headers=headers)

    def post(self, uri, json_body=None, params=None, headers=None):
        return self.request('POST', uri, params=params, json_body=json_body, headers=headers)


def load_field_mapping(path):
    mapping = {}
    if not os.path.exists(path):
        return mapping
    with open(path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            source_id = row.get('source_id')
            target_id = row.get('target_id')
            if source_id and target_id:
                mapping[source_id] = target_id
    return mapping


def save_field_mapping(path, source_fields, target_fields, mapping, notes):
    with open(path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'source_id',
            'source_name',
            'source_type',
            'target_id',
            'target_name',
            'target_type',
            'status',
            'note',
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        target_index = defaultdict(list)
        for target in target_fields:
            key = (target.get('name'), extract_field_type(target))
            target_index[key].append(target)
        for source in source_fields:
            source_id = source.get('id')
            source_name = source.get('name')
            source_type = extract_field_type(source)
            key = (source_name, source_type)
            candidates = target_index.get(key, [])
            target = candidates[0] if candidates else None
            status = 'OK' if len(candidates) == 1 else 'MULTIPLE' if len(candidates) > 1 else 'MISSING'
            note = ''
            if len(candidates) > 1:
                note = f'{len(candidates)} matches for name/type'
            elif not candidates:
                note = 'No matching field found in target'
            writer.writerow({
                'source_id': source_id,
                'source_name': source_name,
                'source_type': source_type,
                'target_id': target.get('id') if target else '',
                'target_name': target.get('name') if target else '',
                'target_type': extract_field_type(target) if target else '',
                'status': status,
                'note': note,
            })
    with open(path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        return {row['source_id']: row['target_id'] for row in reader if row.get('target_id')}


def extract_field_type(field):
    if not field:
        return ''
    schema = field.get('schema') or {}
    return schema.get('type', '')


def build_field_mapping(source_fields, target_fields):
    target_index = defaultdict(list)
    for target in target_fields:
        key = (target.get('name'), extract_field_type(target))
        target_index[key].append(target)
    mapping = {}
    notes = []
    for source in source_fields:
        source_id = source.get('id')
        key = (source.get('name'), extract_field_type(source))
        candidates = target_index.get(key, [])
        if len(candidates) == 1:
            mapping[source_id] = candidates[0].get('id')
        elif len(candidates) > 1:
            mapping[source_id] = candidates[0].get('id')
            notes.append((source_id, 'MULTIPLE', len(candidates)))
        else:
            notes.append((source_id, 'MISSING', 0))
    return mapping, notes


def get_fields(client):
    result = client.get('/rest/api/3/field')
    if not result['ok'] or not isinstance(result['body'], list):
        raise RuntimeError(f'Unable to fetch fields from {client.base_url}: {result["status_code"]}')
    return result['body']


def get_all_workflows(client, query_string=None):
    params = {'expand': 'values.transitions'}
    if query_string:
        params['queryString'] = query_string
    start_at = 0
    max_results = 50
    all_workflows = []
    while True:
        params['startAt'] = str(start_at)
        params['maxResults'] = str(max_results)
        result = client.get('/rest/api/3/workflows/search', params=params)
        if not result['ok']:
            raise RuntimeError(f'Workflow search failed for {client.base_url} query={query_string}: {result["status_code"]}')
        body = result['body'] or {}
        values = body.get('values', [])
        all_workflows.extend(values)
        if body.get('isLast') or len(values) < max_results:
            break
        start_at += len(values)
    return all_workflows


def get_transition_id(transition):
    if transition is None:
        return None
    return transition.get('id') or transition.get('transitionId')


def contains_com_onresolve(obj):
    if isinstance(obj, dict):
        app_key = obj.get('appKey')
        if isinstance(app_key, str) and app_key.startswith(APPKEY_PREFIX):
            return True
        for value in obj.values():
            if contains_com_onresolve(value):
                return True
    elif isinstance(obj, list):
        return any(contains_com_onresolve(item) for item in obj)
    return False


def replace_customfields(obj, mapping):
    if isinstance(obj, dict):
        return {key: replace_customfields(value, mapping) for key, value in obj.items()}
    if isinstance(obj, list):
        return [replace_customfields(item, mapping) for item in obj]
    if isinstance(obj, str):
        def repl(match):
            source = f'customfield_{match.group(1)}'
            return mapping.get(source, source)
        return CUSTOMFIELD_PATTERN.sub(repl, obj)
    return obj


def collect_workflow_conversions(source_workflows, field_mapping):
    conversions = []
    workflow_definitions = []
    for workflow in source_workflows:
        workflow_name = workflow.get('name', '')
        workflow_id = workflow.get('id', '')
        transitions = workflow.get('transitions', []) or []
        transition_count = len(transitions)
        conversion_count = 0
        for transition in transitions:
            transition_id = get_transition_id(transition)
            for obj_type in ('actions', 'validators'):
                for item in transition.get(obj_type, []) or []:
                    if contains_com_onresolve(item):
                        converted = replace_customfields(deepcopy(item), field_mapping)
                        conversion_count += 1
                        conversions.append({
                            'workflow_name': workflow_name,
                            'workflow_id': workflow_id,
                            'transition_id': transition_id,
                            'object_type': obj_type,
                            'appKey': find_appkey(item) or '',
                            'original_json': item,
                            'converted_json': converted,
                            'target_mapping_was_complete': has_all_source_customfields(item, field_mapping),
                        })
        workflow_definitions.append({
            'workflow_name': workflow_name,
            'workflow_id': workflow_id,
            'transition_count': transition_count,
            'conversion_count': conversion_count,
        })
    return conversions, workflow_definitions


def find_appkey(item):
    if isinstance(item, dict):
        app_key = item.get('appKey')
        if isinstance(app_key, str) and app_key.startswith(APPKEY_PREFIX):
            return app_key
        for value in item.values():
            result = find_appkey(value)
            if result:
                return result
    elif isinstance(item, list):
        for entry in item:
            result = find_appkey(entry)
            if result:
                return result
    return None


def has_all_source_customfields(item, mapping):
    text = json.dumps(item, ensure_ascii=False)
    field_ids = set(CUSTOMFIELD_PATTERN.findall(text))
    if not field_ids:
        return True
    return all(f'customfield_{field_id}' in mapping for field_id in field_ids)


def write_workflow_definition_log(path, workflow_definitions):
    with open(path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['workflow_name', 'workflow_id', 'transition_count', 'conversion_count']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in workflow_definitions:
            writer.writerow(row)


def write_workflow_conversion_log(path, conversions):
    with open(path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = [
            'workflow_name',
            'workflow_id',
            'transition_id',
            'object_type',
            'appKey',
            'target_mapping_was_complete',
            'converted_json',
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for record in conversions:
            writer.writerow({
                'workflow_name': record['workflow_name'],
                'workflow_id': record['workflow_id'],
                'transition_id': record['transition_id'],
                'object_type': record['object_type'],
                'appKey': record['appKey'],
                'target_mapping_was_complete': record['target_mapping_was_complete'],
                'converted_json': json.dumps(record['converted_json'], ensure_ascii=False),
            })


def write_workflow_payload_csv_log(csv_writer, payload):
    workflow_name = ''
    workflow_id = ''
    workflows = payload.get('workflows', [])
    if workflows:
        workflow_name = workflows[0].get('name', '')
        workflow_id = workflows[0].get('id', '')
    csv_writer.writerow({
        'workflow_name': workflow_name,
        'workflow_id': workflow_id,
        'payload_json': json.dumps(payload, ensure_ascii=False),
    })


def prepare_target_payloads(target_client, conversions, workflow_limit=0):
    grouped = defaultdict(list)
    for record in conversions:
        grouped[record['workflow_name']].append(record)
    payloads = []
    processed_workflows = 0
    for workflow_name, records in grouped.items():
        if 0 < workflow_limit <= processed_workflows:
            break
        target_response = target_client.get('/rest/api/3/workflows/search', params={'queryString': workflow_name, 'expand': 'values.transitions'})
        if not target_response['ok']:
            print(f'Warning: target workflow search failed for {workflow_name}')
            continue
        target_body = deepcopy(target_response['body'] or {})
        values = target_body.get('values')
        if not isinstance(values, list):
            print(f'Warning: target workflow search returned no values for {workflow_name}')
            continue
        statuses = deepcopy(target_body.get('statuses', []))
        target_workflows = [workflow for workflow in values if workflow.get('name') == workflow_name]
        if not target_workflows:
            print(f'Warning: exact target workflow {workflow_name} not found')
            continue
        for workflow in target_workflows:
            workflow_payload = {'statuses': statuses, 'workflows': [workflow]}
            for record in records:
                if workflow.get('name') != record['workflow_name']:
                    continue
                transition = find_target_transition(workflow, record['transition_id'])
                if transition is None:
                    print(f'Warning: missing transition {record["transition_id"]} in target workflow {workflow_name}')
                    continue
                array_name = record['object_type']
                if array_name not in transition or transition[array_name] is None:
                    transition[array_name] = []
                if not any(compare_objects(existing, record['converted_json']) for existing in transition[array_name]):
                    transition[array_name].append(record['converted_json'])
            payloads.append(workflow_payload)
            processed_workflows += 1
            if 0 < workflow_limit <= processed_workflows:
                break
    return payloads


def find_target_transition(workflow, transition_id):
    for transition in workflow.get('transitions', []) or []:
        if get_transition_id(transition) == transition_id:
            return transition
    return None


def compare_objects(obj_a, obj_b):
    try:
        return json.dumps(obj_a, sort_keys=True, ensure_ascii=False) == json.dumps(obj_b, sort_keys=True, ensure_ascii=False)
    except Exception:
        return obj_a == obj_b


def update_target_workflows(target_client, payloads):
    results = []
    with open(WORKFLOW_UPDATE_PAYLOAD_LOG_CSV, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['workflow_name', 'workflow_id', 'payload_json']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csv_writer.writeheader()
        for payload in payloads:
            if not payload.get('workflows'):
                print('Skipping empty workflow payload.')
                continue
            write_workflow_payload_csv_log(csv_writer, payload)
            response = target_client.post('/rest/api/3/workflows/update', json_body=payload)
            if not response['ok']:
                raise RuntimeError(f'Workflow update failed: {response["status_code"]} {response.get("body")}')
            results.append(response['body'])
    return results


def parse_args():
    parser = argparse.ArgumentParser(description='Migrate Jira workflow scripts from source to target instance.')
    parser.add_argument('--no-regenerate-fields', dest='regenerate_fields', action='store_false', default=True,
                        help='Use existing Fields Mapping.csv if available. Default is to regenerate it.')
    parser.add_argument('--workflow-limit', type=int, default=0,
                        help='If greater than zero, only convert this many workflows for testing.')
    parser.add_argument('--workflow-name', action='append', default=[],
                        help='Name of a workflow to migrate. Can be specified multiple times or as a comma-separated list.')
    return parser.parse_args()


def normalize_workflow_names(workflow_name_args):
    names = []
    for arg in workflow_name_args:
        if arg:
            names.extend([name.strip() for name in arg.split(',') if name.strip()])
    return names


def main():
    args = parse_args()
    selected_workflow_names = normalize_workflow_names(args.workflow_name)
    source_client = JiraClient(SOURCE_BASE_URL, HTTPBasicAuth(SOURCE_USER, SOURCE_TOKEN))
    target_client = JiraClient(TARGET_BASE_URL, HTTPBasicAuth(TARGET_USER, TARGET_TOKEN))

    field_mapping = {}
    if args.regenerate_fields or not os.path.exists(FIELDS_MAPPING_CSV):
        print('Generating field mapping from source and target instances...')
        source_fields = get_fields(source_client)
        target_fields = get_fields(target_client)
        field_mapping, notes = build_field_mapping(source_fields, target_fields)
        field_mapping = save_field_mapping(FIELDS_MAPPING_CSV, source_fields, target_fields, field_mapping, notes)
        print(f'Field mapping saved to {FIELDS_MAPPING_CSV}')
    else:
        print(f'Reading existing field mapping from {FIELDS_MAPPING_CSV}')
        field_mapping = load_field_mapping(FIELDS_MAPPING_CSV)
        if not field_mapping:
            print('Existing mapping file is empty or invalid, regenerating.')
            args.regenerate_fields = True
            main()
            return

    print('Fetching workflows from source instance...')
    source_workflows = get_all_workflows(source_client)
    print(f'Found {len(source_workflows)} workflows in source instance')

    if selected_workflow_names:
        filtered_workflows = [workflow for workflow in source_workflows if workflow.get('name') in selected_workflow_names]
        missing = [name for name in selected_workflow_names if name not in {workflow.get('name') for workflow in source_workflows}]
        if missing:
            print(f'Warning: the following workflow names were not found in source instance: {", ".join(missing)}')
        print(f'Filtering to {len(filtered_workflows)} requested workflows')
        source_workflows = filtered_workflows

    conversions, workflow_definitions = collect_workflow_conversions(source_workflows, field_mapping)
    write_workflow_definition_log(WORKFLOW_DEFINITION_LOG_CSV, workflow_definitions)
    write_workflow_conversion_log(WORKFLOW_CONVERSION_LOG_CSV, conversions)
    print(f'Workflow definitions logged to {WORKFLOW_DEFINITION_LOG_CSV}')
    print(f'Workflow conversions logged to {WORKFLOW_CONVERSION_LOG_CSV}')

    if not conversions:
        print('No workflow actions or validators requiring conversion were found. Exiting.')
        return

    payloads = prepare_target_payloads(target_client, conversions, workflow_limit=args.workflow_limit)
    if not payloads:
        print('No target workflows were prepared for update. Exiting.')
        return

    print('Posting converted workflows to target instance...')
    update_results = update_target_workflows(target_client, payloads)
    print(f'Updated {len(update_results)} workflows on target instance.')


if __name__ == '__main__':
    main()

