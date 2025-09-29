#!/bin/bash
# Post-Deployment Validation Script
# Verifies that cross-repository ADR system was deployed correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Post-Deployment Validation${NC}"
echo ""

ERRORS=0
WARNINGS=0

# Function to report error
report_error() {
    echo -e "  ${RED}❌ $1${NC}"
    ((ERRORS++))
}

# Function to report warning
report_warning() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

# Function to report success
report_success() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

# Check directory structure
echo -e "${BLUE}📁 Checking directory structure...${NC}"

if [ -d "docs/ADR" ]; then
    report_success "docs/ADR directory exists"
else
    report_error "docs/ADR directory missing"
fi

if [ -d "ops/ADR" ]; then
    report_success "ops/ADR directory exists"
else
    report_error "ops/ADR directory missing"
fi

# Check core files
echo -e "${BLUE}📄 Checking core files...${NC}"

# Check for cross-repo ADR standard
CROSS_REPO_ADR=$(find docs/ADR -name "*cross-repository*" -o -name "*cross-repo*" | head -1)
if [ -n "$CROSS_REPO_ADR" ]; then
    report_success "Cross-repository ADR standard found: $(basename "$CROSS_REPO_ADR")"
else
    report_error "Cross-repository ADR standard not found"
fi

# Check ADR template
if [ -f "docs/ADR/ADR-template.md" ]; then
    if grep -q "external_related" "docs/ADR/ADR-template.md"; then
        report_success "ADR template has cross-repository fields"
    else
        report_warning "ADR template missing cross-repository fields"
    fi
else
    report_error "ADR template not found"
fi

# Check repository mapping
if [ -f "docs/ADR/repository-mapping.yaml" ]; then
    if grep -q "repositories:" "docs/ADR/repository-mapping.yaml"; then
        if grep -q "your-github-org" "docs/ADR/repository-mapping.yaml"; then
            report_warning "Repository mapping contains template placeholders - needs customization"
        else
            report_success "Repository mapping appears customized"
        fi
    else
        report_error "Repository mapping has invalid format"
    fi
else
    report_error "Repository mapping not found"
fi

# Check validation scripts
echo -e "${BLUE}🔧 Checking validation scripts...${NC}"

if [ -f "ops/ADR/validate_cross_repo_links.sh" ]; then
    if [ -x "ops/ADR/validate_cross_repo_links.sh" ]; then
        report_success "Link validation script is executable"
    else
        report_warning "Link validation script not executable"
    fi
else
    report_error "Link validation script not found"
fi

if [ -f "ops/ADR/check_alignment_drift.sh" ]; then
    if [ -x "ops/ADR/check_alignment_drift.sh" ]; then
        report_success "Drift check script is executable"
    else
        report_warning "Drift check script not executable"
    fi
else
    report_warning "Drift check script not found"
fi

# Check .gitignore
echo -e "${BLUE}🚫 Checking .gitignore...${NC}"

if [ -f ".gitignore" ]; then
    if grep -q "Cross-Repository ADR System" .gitignore; then
        report_success ".gitignore has ADR system entries"
    else
        report_warning ".gitignore missing ADR system entries"
    fi
else
    report_warning ".gitignore not found"
fi

# Check ADR index
echo -e "${BLUE}📚 Checking ADR index...${NC}"

if [ -f "docs/ADR/INDEX.md" ]; then
    if [ -n "$CROSS_REPO_ADR" ]; then
        ADR_NUMBER=$(basename "$CROSS_REPO_ADR" | grep -o "ADR-[0-9]*" | head -1)
        if grep -q "$ADR_NUMBER" "docs/ADR/INDEX.md"; then
            report_success "Cross-repository ADR listed in index"
        else
            report_warning "Cross-repository ADR not listed in index"
        fi
    fi
else
    report_warning "ADR index not found"
fi

# Test validation script
echo -e "${BLUE}🧪 Testing validation functionality...${NC}"

if [ -f "ops/ADR/validate_cross_repo_links.sh" ] && [ -x "ops/ADR/validate_cross_repo_links.sh" ]; then
    echo "  Testing link validation script..."
    if ./ops/ADR/validate_cross_repo_links.sh > /dev/null 2>&1; then
        report_success "Link validation script runs successfully"
    else
        # Check if it's just because there are no cross-repo links yet
        if [ $? -eq 1 ]; then
            report_warning "Link validation found issues (expected if no cross-repo links configured yet)"
        else
            report_error "Link validation script failed to run"
        fi
    fi
else
    report_error "Cannot test link validation script"
fi

# Summary
echo ""
echo -e "${BLUE}📊 Validation Summary:${NC}"
echo "  Errors: $ERRORS"
echo "  Warnings: $WARNINGS"

if [ $ERRORS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 Deployment validation passed!${NC}"
    echo ""
    echo -e "${BLUE}🎯 Recommended next steps:${NC}"
    echo "1. Customize docs/ADR/repository-mapping.yaml with your repository details"
    echo "2. Add cross-repository references to existing ADRs"
    echo "3. Run: ./ops/ADR/validate_cross_repo_links.sh"
    echo "4. Add validation to your CI workflow"
    echo ""
    exit 0
else
    echo ""
    echo -e "${RED}❌ Deployment validation failed!${NC}"
    echo "Please fix the errors above before proceeding."
    echo ""
    exit 1
fi