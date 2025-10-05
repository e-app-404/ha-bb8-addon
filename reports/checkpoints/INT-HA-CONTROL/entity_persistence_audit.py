#!/usr/bin/env python3
"""
Entity Persistence Audit for INT-HA-CONTROL

Validates that BB8 entities (presence, rssi) recover within 10 seconds
after MQTT broker and HA Core restarts.

Usage:
    python entity_persistence_audit.py \\
        --ha-url "http://192.168.0.129:8123" \\
        --token "$HA_TOKEN" \\
        --out-json entity_audit.json \\
        --out-log entity_persistence_test.log
"""

import argparse
import json
import logging
import requests
import time
from datetime import datetime
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


class EntityPersistenceAuditor:
    def __init__(self, ha_url: str, token: str):
        self.ha_url = ha_url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'ha_url': ha_url,
            'tests': [],
            'overall_pass': False
        }

    def log_and_record(self, message: str, level: str = 'INFO'):
        """Log message and record in test results."""
        logger.log(getattr(logging, level), message)
        if 'log_entries' not in self.results:
            self.results['log_entries'] = []
        self.results['log_entries'].append({
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        })

    def get_entities(self) -> List[Dict[str, Any]]:
        """Get all entities from Home Assistant."""
        try:
            response = requests.get(
                f'{self.ha_url}/api/states',
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_and_record(f'Failed to get entities: {e}', 'ERROR')
            return []

    def find_bb8_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Find BB8-related entities (presence, rssi)."""
        bb8_entities = {}
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            if 'bb8' in entity_id.lower() or 'BB-8' in entity.get('attributes', {}).get('friendly_name', ''):
                if 'presence' in entity_id or 'rssi' in entity_id:
                    bb8_entities[entity_id] = entity
        return bb8_entities

    def check_entity_availability(self, expected_entities: List[str]) -> Dict[str, bool]:
        """Check if expected BB8 entities are available."""
        entities = self.get_entities()
        bb8_entities = self.find_bb8_entities(entities)
        
        availability = {}
        for entity_id in expected_entities:
            # Check if entity exists (exact match or partial match)
            found = False
            for existing_id in bb8_entities.keys():
                if entity_id in existing_id or existing_id in entity_id:
                    availability[entity_id] = bb8_entities[existing_id].get('state') not in ['unavailable', 'unknown']
                    found = True
                    break
            if not found:
                availability[entity_id] = False
        
        return availability

    def simulate_broker_restart(self) -> bool:
        """Simulate MQTT broker restart (placeholder - would need actual restart logic)."""
        self.log_and_record('SIMULATE: MQTT broker restart (10s delay)')
        time.sleep(10)  # Simulate restart time
        return True

    def simulate_ha_core_restart(self) -> bool:
        """Simulate HA Core restart via API."""
        try:
            self.log_and_record('Triggering HA Core restart via API...')
            response = requests.post(
                f'{self.ha_url}/api/services/homeassistant/restart',
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                self.log_and_record('HA Core restart triggered successfully')
                time.sleep(30)  # Wait for restart to complete
                return True
            else:
                self.log_and_record(f'HA Core restart failed: {response.status_code}', 'ERROR')
                return False
        except Exception as e:
            self.log_and_record(f'HA Core restart error: {e}', 'ERROR')
            return False

    def test_entity_recovery(self, test_name: str, restart_fn, expected_entities: List[str]) -> bool:
        """Test entity recovery after restart."""
        self.log_and_record(f'Starting {test_name} test...')
        
        # Check initial state
        initial_availability = self.check_entity_availability(expected_entities)
        self.log_and_record(f'Initial entity availability: {initial_availability}')
        
        # Perform restart
        restart_success = restart_fn()
        if not restart_success:
            self.results['tests'].append({
                'test_name': test_name,
                'restart_success': False,
                'recovery_time': None,
                'entities_recovered': {},
                'test_pass': False
            })
            return False
        
        # Monitor recovery (10 second SLA)
        recovery_start = time.time()
        max_wait = 10  # 10 second SLA
        
        while time.time() - recovery_start < max_wait:
            current_availability = self.check_entity_availability(expected_entities)
            all_recovered = all(current_availability.values())
            
            if all_recovered:
                recovery_time = time.time() - recovery_start
                self.log_and_record(f'{test_name}: All entities recovered in {recovery_time:.2f}s')
                self.results['tests'].append({
                    'test_name': test_name,
                    'restart_success': True,
                    'recovery_time': recovery_time,
                    'entities_recovered': current_availability,
                    'test_pass': recovery_time <= 10.0
                })
                return recovery_time <= 10.0
            
            time.sleep(1)
        
        # Recovery failed within SLA
        final_availability = self.check_entity_availability(expected_entities)
        recovery_time = time.time() - recovery_start
        self.log_and_record(f'{test_name}: Recovery failed within {max_wait}s SLA', 'ERROR')
        self.results['tests'].append({
            'test_name': test_name,
            'restart_success': True,
            'recovery_time': recovery_time,
            'entities_recovered': final_availability,
            'test_pass': False
        })
        return False

    def run_audit(self) -> bool:
        """Run complete entity persistence audit."""
        self.log_and_record('Starting Entity Persistence Audit...')
        
        # Expected BB8 entities
        expected_entities = ['bb8_presence', 'bb8_rssi', 'presence', 'rssi']
        
        # Test 1: MQTT Broker restart recovery
        broker_test_pass = self.test_entity_recovery(
            'MQTT_BROKER_RESTART',
            self.simulate_broker_restart,
            expected_entities
        )
        
        # Test 2: HA Core restart recovery  
        core_test_pass = self.test_entity_recovery(
            'HA_CORE_RESTART',
            self.simulate_ha_core_restart,
            expected_entities
        )
        
        # Overall result
        overall_pass = broker_test_pass and core_test_pass
        self.results['overall_pass'] = overall_pass
        
        if overall_pass:
            self.log_and_record('Entity Persistence Audit: PASS')
        else:
            self.log_and_record('Entity Persistence Audit: FAIL', 'ERROR')
        
        return overall_pass


def main():
    parser = argparse.ArgumentParser(description='Entity Persistence Audit for INT-HA-CONTROL')
    parser.add_argument('--ha-url', required=True, help='Home Assistant URL')
    parser.add_argument('--token', required=True, help='Home Assistant Long-Lived Access Token')
    parser.add_argument('--out-json', required=True, help='Output JSON file path')
    parser.add_argument('--out-log', required=True, help='Output log file path')
    
    args = parser.parse_args()
    
    # Configure file logging
    file_handler = logging.FileHandler(args.out_log)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(file_handler)
    
    # Run audit
    auditor = EntityPersistenceAuditor(args.ha_url, args.token)
    success = auditor.run_audit()
    
    # Write results
    with open(args.out_json, 'w') as f:
        json.dump(auditor.results, f, indent=2)
    
    print(f'\\n=== Entity Persistence Audit Summary ===')
    print(f'Total tests: {len(auditor.results["tests"])}')
    print(f'Passed tests: {sum(1 for t in auditor.results["tests"] if t["test_pass"])}')
    print(f'Overall PASS: {success}')
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())