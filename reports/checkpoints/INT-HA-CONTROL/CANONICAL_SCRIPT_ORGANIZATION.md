# INT-HA-CONTROL v1.1.1 Canonical Script Organization

## ✅ **CORRECTED CANONICAL LOCATIONS**

### **Operational Scripts**
According to **ADR-0019** workspace folder taxonomy, scripts must be placed in canonical locations:

```
ops/evidence/execute_int_ha_control.sh    # ✅ CANONICAL - Operational execution with credentials
reports/checkpoints/INT-HA-CONTROL/       # ✅ CANONICAL - Framework components
```

### **Workspace Organization Rules**

**From ADR-0019:**
- `ops/`: **Operations, QA, audits, release tooling**
  - Subfolders: `ops/audit`, `ops/diagnostics`, `ops/qa`, `ops/release`, `ops/evidence`
  - **Operational CLIs** → `ops/tools/` or appropriate subfolder
- `scripts/`: **Repo developer scripts** (small glue, bootstrap, repo maintenance)
- `reports/`: **Important documentation for retention** (checkpoints, governance)

### **✗ VIOLATIONS CORRECTED:**
- ~~`./execute_int_ha_control.sh`~~ → `ops/evidence/execute_int_ha_control.sh`
- Repository root must **NOT** contain operational scripts

## **🎯 USAGE:**

### **Framework Development (Internal):**
```bash
cd reports/checkpoints/INT-HA-CONTROL/
./execute_int_ha_control.sh
```

### **Operational Validation (Production):**
```bash
# From repository root
HOST=192.168.0.129 PORT=1883 USER=mqtt_bb8 PASS=mqtt_bb8 BASE=bb8 ops/evidence/execute_int_ha_control.sh
```

### **Script Responsibilities:**

1. **`ops/evidence/execute_int_ha_control.sh`**:
   - Canonical operational entry point
   - Credential validation and MQTT connectivity
   - Repo-relative path resolution
   - Mandatory artifact validation
   - Production-ready execution with error handling

2. **`reports/checkpoints/INT-HA-CONTROL/execute_int_ha_control.sh`**:
   - Framework component execution  
   - P0-P3 validation protocol
   - QA integration suite coordination
   - Development/testing context

## **📋 ADR-0019 COMPLIANCE:**

✅ **Operational scripts** → `ops/evidence/` (evidence collection context)
✅ **Framework artifacts** → `reports/checkpoints/` (important documentation)  
✅ **No repo root scripts** → Canonical placement enforced
✅ **Clear separation** → Operational vs. development contexts

This organization maintains clear boundaries between:
- **Development/testing** workflows (reports/checkpoints/)
- **Operational/production** workflows (ops/evidence/)
- **Repository maintenance** (scripts/ - not used here)

The canonical structure ensures proper governance, reduces confusion, and maintains workspace hygiene per established ADR standards.