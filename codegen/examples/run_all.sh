#!/usr/bin/env bash
# ============================================================
# Graph-RAG Code Completion Examples - Run All Tests
# ============================================================
# Usage:
#   ./run_all.sh index          # Index the demo project
#   ./run_all.sh fim <file>     # Run a single FIM example
#   ./run_all.sh rag <file>     # Run a single RAG example
#   ./run_all.sh all            # Run all examples
#   ./run_all.sh compare <file> # Compare FIM vs RAG on same file
# ============================================================

set -euo pipefail

HOST="${HOST:-http://localhost:8000}"
PROJECT_PATH="$(cd "$(dirname "$0")" && pwd)/demo_project"
EXAMPLES_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

# ----- Helper Functions -----
divider() {
    echo -e "\n${BLUE}=====================================================================${NC}\n"
}

section() {
    echo -e "\n${BOLD}${CYAN}>>> $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

check_server() {
    if ! curl -s --max-time 3 "$HOST/api/v1/models" > /dev/null 2>&1; then
        echo -e "${RED}Error: Server not running at $HOST${NC}"
        echo "Start the server first: cd .. && python3 manage.py runserver"
        exit 1
    fi
    success "Server OK: $HOST"
}

# Extract content around <cursor> tag
# Sets global vars: $FILE_PROMPT, $FILE_SUFFIX, $FILE_INCLUDES
extract_from_file() {
    local file="$1"

    # Extract everything before <cursor> as prompt
    FILE_PROMPT=$(sed '0,/<\/\?cursor>/!d' "$file" | head -n -1)

    # Extract everything after <cursor> as suffix
    FILE_SUFFIX=$(sed '0,/<\/\?cursor>/d' "$file" | tail -n +2)

    # Auto-extract #include lines for includes
    FILE_INCLUDES=$(echo "$FILE_PROMPT" | grep -E '^#include' || true)
    if [ -z "$FILE_INCLUDES" ]; then
        FILE_INCLUDES="[]"
    else
        FILE_INCLUDES=$(echo "$FILE_INCLUDES" | jq -R -s -c 'split("\n") | map(select(length > 0))')
    fi
}

# Run FIM completion
run_fim() {
    local file="$1"
    local label="$2"

    extract_from_file "$file"

    local prompt_json
    prompt_json=$(echo -n "$FILE_PROMPT" | jq -Rs .)
    local suffix_json
    suffix_json=$(echo -n "$FILE_SUFFIX" | jq -Rs .)

    echo -e "${BOLD}File:${NC} $label"
    echo -e "${BOLD}Type:${NC} FIM (DeepSeek Fill-in-Middle)"
    divider

    local response
    response=$(curl -s --max-time 15 -X POST "$HOST/api/v1/completion" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg prompt "$FILE_PROMPT" \
            --arg suffix "$FILE_SUFFIX" \
            --argjson includes "$FILE_INCLUDES" \
            '{prompt: $prompt, suffix: $suffix, includes: ($includes | .[0:5]), max_tokens: 150}')" 2>&1) || response='{"error": "timeout"}'

    echo -e "${YELLOW}--- Prompt (before <cursor>) ---${NC}"
    echo "$FILE_PROMPT" | tail -n 10
    echo -e "\n${YELLOW}--- Suffix (after <cursor>) ---${NC}"
    echo "$FILE_SUFFIX" | head -n 10
    divider
    echo -e "${GREEN}--- LLM Suggestion ---${NC}"

    if echo "$response" | jq -e '.success' > /dev/null 2>&1; then
        echo "$response" | jq -r '.suggestion.text // .suggestion // "No suggestion"'
    else
        echo -e "${RED}Error: $(echo "$response" | jq -r '.error // .error_code // "Unknown"' 2>/dev/null)${NC}"
    fi
    divider
}

# Run RAG completion (Chat API)
run_rag() {
    local file="$1"
    local label="$2"

    extract_from_file "$file"

    echo -e "${BOLD}File:${NC} $label"
    echo -e "${BOLD}Type:${NC} RAG (Chat API + Graph-RAG Knowledge Base)"
    divider

    local response
    response=$(curl -s --max-time 30 -X POST "$HOST/api/v1/chat" \
        -H "Content-Type: application/json" \
        -d "$(jq -n \
            --arg prompt "$FILE_PROMPT" \
            --arg suffix "$FILE_SUFFIX" \
            --arg project "demo_project" \
            '{
                context: {prompt: $prompt, suffix: $suffix, includes: []},
                model: "deepseek-chat",
                max_tokens: 500,
                provider: "deepseek",
                use_rag: true,
                use_graph_rag: true,
                project_path: "demo_project"
            }')" 2>&1) || response='{"error": "timeout"}'

    echo -e "${YELLOW}--- Prompt (before <cursor>) ---${NC}"
    echo "$FILE_PROMPT" | tail -n 10
    echo -e "\n${YELLOW}--- Suffix (after <cursor>) ---${NC}"
    echo "$FILE_SUFFIX" | head -n 10
    divider
    echo -e "${GREEN}--- LLM Response ---${NC}"

    if echo "$response" | jq -e '.success' > /dev/null 2>&1; then
        echo "$response" | jq -r '.response.text // .response.choices[0].message.content // .response // "No response"'
    else
        echo -e "${RED}Error: $(echo "$response" | jq -r '.error // .error_code // "Unknown"' 2>/dev/null)${NC}"
    fi
    divider
}

# ----- Indexing -----
do_index() {
    section "Indexing demo project for RAG..."
    echo "Project path: $PROJECT_PATH"
    echo ""

    # Try using the project's indexer
    cd "$(dirname "$0")/.."
    local indexer_cmd="pixi run python -m completion.rag.indexer index $PROJECT_PATH --project-path demo_project"
    echo -e "${YELLOW}Running: ${indexer_cmd}${NC}"
    echo ""

    if command -v pixi &>/dev/null; then
        HF_ENDPOINT=https://hf-mirror.com TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 $indexer_cmd 2>&1
        if [ $? -eq 0 ]; then
            success "Indexing complete"
        else
            echo -e "${YELLOW}Warning: Indexer failed.${NC}"
        fi
    elif command -v python3 &>/dev/null; then
        if python3 -m completion.rag.indexer index $PROJECT_PATH --project-path demo_project 2>&1; then
            success "Indexing complete"
        else
            echo -e "${YELLOW}Warning: Indexer not available. Install dependencies first.${NC}"
        fi
    else
        echo -e "${YELLOW}Python3 not found.${NC}"
    fi
}

# ----- Compare FIM vs RAG on same file -----
do_compare() {
    local file="$1"
    local label
    label=$(basename "$file")

    divider
    echo -e "${BOLD}${CYAN}  COMPARISON: FIM vs RAG - $(basename "$file")${NC}"
    echo -e "${CYAN}  <cursor> = where completion should be inserted${NC}"
    divider

    echo -e "\n${BOLD}--- FIM Completion ---${NC}"
    run_fim "$file" "$label"

    echo -e "\n${BOLD}--- RAG Completion ---${NC}"
    run_rag "$file" "$label"
}

# ----- Main -----
show_usage() {
    echo -e "${BOLD}Graph-RAG Code Completion Examples${NC}"
    echo ""
    echo "Usage:"
    echo "  $0 index                        Index the demo project for RAG"
    echo "  $0 fim <file>                   Run FIM completion on a file"
    echo "  $0 rag <file>                   Run RAG completion on a file"
    echo "  $0 compare <file>               Compare FIM vs RAG on same file"
    echo "  $0 all                          Run all examples"
    echo "  $0 list                         List all available example files"
    echo ""
    echo "Available FIM examples:"
    echo "  fim_quick_sort        - Template quick sort partition logic"
    echo "  fim_smart_pointer     - Custom UniquePtr implementation"
    echo "  fim_event_bus         - Event publish/subscribe system"
    echo "  fim_thread_pool       - Thread pool worker join loop"
    echo "  fim_config_loader     - Config parser API surface"
    echo ""
    echo "Available RAG examples (use demo_project types):"
    echo "  rag_setup_renderer    - Render setup with Scene/Mesh/Material/Camera"
    echo "  rag_raycast_scene     - Ray-AABB intersection traversal"
    echo "  rag_pbr_shader        - PBR shader program creation"
    echo "  rag_frustum_cull      - Frustum culling with spatial queries"
    echo "  rag_mesh_loader       - Procedural sphere generator"
    echo "  rag_transform_hierarchy - Scene graph world transform update"
    echo "  rag_scene_traversal   - Sorted command collection by depth"
    echo ""
    echo "Example:"
    echo "  $0 compare $EXAMPLES_DIR/rag_setup_renderer.cpp"
    echo ""
    echo "Server: ${HOST}"
}

case "${1:-}" in
    index)
        do_index
        ;;
    fim)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 fim <file>"
            exit 1
        fi
        check_server
        run_fim "$2" "$(basename "$2")"
        ;;
    rag)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 rag <file>"
            exit 1
        fi
        check_server
        run_rag "$2" "$(basename "$2")"
        ;;
    compare)
        if [ $# -lt 2 ]; then
            echo "Usage: $0 compare <file>"
            exit 1
        fi
        check_server
        do_compare "$2"
        ;;
    all)
        check_server
        echo -e "${BOLD}Running ALL examples (FIM + RAG)...${NC}"

        # FIM examples
        for f in "$EXAMPLES_DIR"/fim_*.cpp; do
            do_compare "$f"
        done

        # RAG examples
        for f in "$EXAMPLES_DIR"/rag_*.cpp; do
            do_compare "$f"
        done
        ;;
    list)
        echo -e "${BOLD}FIM examples:${NC}"
        for f in "$EXAMPLES_DIR"/fim_*.cpp; do
            echo "  $(basename "$f")"
        done
        echo ""
        echo -e "${BOLD}RAG examples:${NC}"
        for f in "$EXAMPLES_DIR"/rag_*.cpp; do
            echo "  $(basename "$f")"
        done
        ;;
    server|ping)
        check_server
        ;;
    *)
        show_usage
        ;;
esac
