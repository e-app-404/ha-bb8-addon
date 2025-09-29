#!/bin/bash
# Cross-Repository ADR System Deployment Script
# Automated deployment of cross-repository ADR linking system

set -e

# Configuration
BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$(pwd)"
ADR_DIR="docs/ADR"
OPS_DIR="ops/ADR"
BACKUP_SUFFIX="_backup_$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Cross-Repository ADR System Deployment${NC}"
echo "Bundle: $BUNDLE_DIR"
echo "Target: $TARGET_DIR"
echo ""

# Verify we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Must be run from the root of a git repository${NC}"
    exit 1
fi

# Create necessary directories
echo -e "${BLUE}📁 Creating directory structure...${NC}"
mkdir -p "$ADR_DIR"
mkdir -p "$OPS_DIR"
echo "  ✓ Created $ADR_DIR"
echo "  ✓ Created $OPS_DIR"

# Function to backup existing file
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        local backup="${file}${BACKUP_SUFFIX}"
        cp "$file" "$backup"
        echo -e "  ${YELLOW}📋 Backed up existing file to $(basename "$backup")${NC}"
    fi
}

# Function to get next ADR number
get_next_adr_number() {
    local max_num=0
    if [ -d "$ADR_DIR" ]; then
        for file in "$ADR_DIR"/ADR-*.md; do
            if [ -f "$file" ]; then
                local num=$(basename "$file" | sed 's/ADR-0*\([0-9]\+\)-.*/\1/')
                if [ "$num" -gt "$max_num" ]; then
                    max_num="$num"
                fi
            fi
        done
    fi
    printf "%04d" $((max_num + 1))
}

# Deploy core ADR standard
echo -e "${BLUE}📄 Deploying Cross-Repository ADR Standard...${NC}"
NEXT_ADR=$(get_next_adr_number)
ADR_FILENAME="ADR-${NEXT_ADR}-cross-repository-adr-alignment.md"
TARGET_ADR="$ADR_DIR/$ADR_FILENAME"

if [ -f "$TARGET_ADR" ]; then
    backup_file "$TARGET_ADR"
fi

# Copy and customize the ADR standard template
cp "$BUNDLE_DIR/templates/ADR-XXXX-cross-repo-standard.md" "$TARGET_ADR"
sed -i.tmp "s/ADR-XXXX/ADR-${NEXT_ADR}/g" "$TARGET_ADR"
sed -i.tmp "s/YYYY-MM-DD/$(date +%Y-%m-%d)/g" "$TARGET_ADR"
rm -f "${TARGET_ADR}.tmp"

echo "  ✓ Created $ADR_FILENAME"

# Deploy enhanced ADR template
echo -e "${BLUE}📝 Deploying enhanced ADR template...${NC}"
ADR_TEMPLATE="$ADR_DIR/ADR-template.md"
if [ -f "$ADR_TEMPLATE" ]; then
    backup_file "$ADR_TEMPLATE"
    echo -e "  ${YELLOW}⚠️  Existing ADR template backed up${NC}"
    echo -e "  ${YELLOW}⚠️  Manual merge may be required${NC}"
fi

cp "$BUNDLE_DIR/templates/ADR-template-enhanced.md" "$ADR_TEMPLATE"
echo "  ✓ Updated ADR template with cross-repository fields"

# Deploy repository mapping configuration
echo -e "${BLUE}🗺️  Deploying repository mapping configuration...${NC}"
REPO_MAPPING="$ADR_DIR/repository-mapping.yaml"
if [ -f "$REPO_MAPPING" ]; then
    backup_file "$REPO_MAPPING"
    echo -e "  ${YELLOW}⚠️  Existing repository mapping backed up${NC}"
else
    cp "$BUNDLE_DIR/templates/repository-mapping.yaml.template" "$REPO_MAPPING"
    echo "  ✓ Created repository-mapping.yaml"
    echo -e "  ${YELLOW}⚠️  CUSTOMIZE: Edit $REPO_MAPPING with your repository details${NC}"
fi

# Deploy alignment status template
echo -e "${BLUE}📊 Deploying alignment status template...${NC}"
ALIGNMENT_STATUS="$ADR_DIR/alignment-status.yaml"
if [ ! -f "$ALIGNMENT_STATUS" ]; then
    cp "$BUNDLE_DIR/templates/alignment-status.yaml.template" "$ALIGNMENT_STATUS"
    sed -i.tmp "s/YYYY-MM-DD/$(date +%Y-%m-%d)/g" "$ALIGNMENT_STATUS"
    sed -i.tmp "s/YYYY-MM-DDTHH:MM:SSZ/$(date -u +%Y-%m-%dT%H:%M:%SZ)/g" "$ALIGNMENT_STATUS"
    rm -f "${ALIGNMENT_STATUS}.tmp"
    echo "  ✓ Created alignment-status.yaml template"
else
    echo "  ℹ️  Alignment status file already exists (not overwritten)"
fi

# Deploy validation scripts
echo -e "${BLUE}🔧 Deploying validation scripts...${NC}"

# Copy main validation script
if [ -f "$BUNDLE_DIR/../../../ops/ADR/validate_cross_repo_links.sh" ]; then
    cp "$BUNDLE_DIR/../../../ops/ADR/validate_cross_repo_links.sh" "$OPS_DIR/"
    chmod +x "$OPS_DIR/validate_cross_repo_links.sh"
    echo "  ✓ Deployed validate_cross_repo_links.sh"
else
    echo -e "  ${YELLOW}⚠️  Cross-repo validation script not found in bundle${NC}"
fi

# Create basic drift check script
cat > "$OPS_DIR/check_alignment_drift.sh" << 'EOF'
#!/bin/bash
# Basic Alignment Drift Check Script
# TODO: Implement full drift detection logic

echo "🔍 Checking for ADR alignment drift..."

if [ ! -f "docs/ADR/alignment-status.yaml" ]; then
    echo "⚠️  No alignment status file found"
    echo "   Run validation first or create alignment entries"
    exit 0
fi

echo "📋 Alignment status file found"
echo "💡 TODO: Implement drift detection by:"
echo "   1. Parsing alignment-status.yaml"
echo "   2. Fetching upstream ADR last_updated dates"
echo "   3. Comparing with local last_checked dates"
echo "   4. Reporting drift and required actions"

echo "✅ Drift check placeholder completed"
EOF

chmod +x "$OPS_DIR/check_alignment_drift.sh"
echo "  ✓ Created check_alignment_drift.sh (basic implementation)"

# Update .gitignore
echo -e "${BLUE}🚫 Updating .gitignore...${NC}"
GITIGNORE_ADDITIONS="$BUNDLE_DIR/templates/gitignore-additions.txt"

cat > "$GITIGNORE_ADDITIONS" << 'EOF'
# Cross-Repository ADR System
# Add these entries to your .gitignore

# ADR alignment tracking (auto-generated)
docs/ADR/alignment-status.yaml

# Deployment bundle (remove after deployment)
docs/ADR/deployment-bundle/
deployment-bundle/
EOF

if [ -f ".gitignore" ]; then
    if ! grep -q "Cross-Repository ADR System" .gitignore; then
        echo "" >> .gitignore
        cat "$GITIGNORE_ADDITIONS" >> .gitignore
        echo "  ✓ Added entries to .gitignore"
    else
        echo "  ℹ️  .gitignore already contains ADR system entries"
    fi
else
    cp "$GITIGNORE_ADDITIONS" .gitignore
    echo "  ✓ Created .gitignore with ADR system entries"
fi

# Update ADR index if it exists
echo -e "${BLUE}📚 Updating ADR index...${NC}"
ADR_INDEX="$ADR_DIR/INDEX.md"
if [ -f "$ADR_INDEX" ]; then
    if ! grep -q "$ADR_FILENAME" "$ADR_INDEX"; then
        # Add entry to ADR list
        sed -i.tmp "/^- \[ADR-[0-9]/a\\
- [ADR-${NEXT_ADR}] Cross-Repository ADR Alignment and Linking Standard" "$ADR_INDEX"
        
        # Add reference link at bottom
        sed -i.tmp "/^\[ADR-[0-9]/a\\
[ADR-${NEXT_ADR}]: $ADR_FILENAME" "$ADR_INDEX"
        
        rm -f "${ADR_INDEX}.tmp"
        echo "  ✓ Added ADR-${NEXT_ADR} to INDEX.md"
    else
        echo "  ℹ️  ADR already listed in index"
    fi
else
    echo "  ℹ️  No ADR index found (INDEX.md)"
fi

# Deployment summary
echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. 🎯 CUSTOMIZE repository-mapping.yaml with your repository details"
echo "2. 📝 Update $ADR_FILENAME with repository-specific information"
echo "3. 🔗 Add cross-repository references to existing ADRs"
echo "4. ✅ Run validation: ./ops/ADR/validate_cross_repo_links.sh"
echo "5. 🔄 Add validation to your CI workflow"
echo ""
echo -e "${YELLOW}⚠️  Files backed up with suffix: ${BACKUP_SUFFIX}${NC}"
echo ""
echo -e "${BLUE}📖 Documentation:${NC}"
echo "- Deployment bundle README: $BUNDLE_DIR/README.md"
echo "- Copilot instructions: $BUNDLE_DIR/COPILOT-INSTRUCTIONS.md"
echo "- Cross-repo ADR standard: $TARGET_ADR"

# Post-deployment validation
echo ""
echo -e "${BLUE}🔍 Running post-deployment validation...${NC}"
if [ -f "$BUNDLE_DIR/scripts/post_deploy_validation.sh" ]; then
    "$BUNDLE_DIR/scripts/post_deploy_validation.sh"
else
    echo "  ℹ️  Post-deployment validation script not found"
fi