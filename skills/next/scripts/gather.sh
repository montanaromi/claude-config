#!/bin/bash
# Gathers journal context for the /next skill
# Outputs structured data: today's journal, recent carry-overs, time-of-day, workload stats

NOTES_DIR="$HOME/notes"
TODAY=$(date +%Y-%m-%d)
YEAR=$(date +%Y)
MONTH=$(date +%m)
HOUR=$(date +%H)
TODAY_FILE="$NOTES_DIR/$YEAR/$MONTH/$TODAY.md"

# --- Time of day ---
echo "=== TIME_CONTEXT ==="
echo "current_time: $(date +%H:%M)"
if (( HOUR < 12 )); then
  echo "period: morning"
  echo "suggestion: Good time for syncs, emails, meetings, and communication tasks."
elif (( HOUR < 17 )); then
  echo "period: afternoon"
  echo "suggestion: Good time for deep work — writing, reviews, coding, complex tasks."
else
  echo "period: evening"
  echo "suggestion: Wind down with quick wins and close out items. Avoid starting large tasks."
fi

# --- Today's journal ---
echo ""
echo "=== TODAY_JOURNAL ==="
if [[ -f "$TODAY_FILE" ]]; then
  cat "$TODAY_FILE"
else
  echo "(no journal for today)"
fi

# --- Workload stats ---
echo ""
echo "=== WORKLOAD_STATS ==="
if [[ -f "$TODAY_FILE" ]]; then
  todo_count=$(grep -c '^\- \[TODO\]' "$TODAY_FILE" 2>/dev/null)
  todo_count=${todo_count:-0}
  ip_count=$(grep -c '^\- \[IN_PROGRESS\]' "$TODAY_FILE" 2>/dev/null)
  ip_count=${ip_count:-0}
  done_count=$(grep -c '^\- \[DONE\]' "$TODAY_FILE" 2>/dev/null)
  done_count=${done_count:-0}
  blocked_count=$(grep -c '^\- \[BLOCKED\]' "$TODAY_FILE" 2>/dev/null)
  blocked_count=${blocked_count:-0}
  echo "todo: $todo_count"
  echo "in_progress: $ip_count"
  echo "done: $done_count"
  echo "blocked: $blocked_count"
  echo "total_open: $((todo_count + ip_count + blocked_count))"
else
  echo "todo: 0"
  echo "in_progress: 0"
  echo "done: 0"
  echo "blocked: 0"
  echo "total_open: 0"
fi

# --- Carry-over detection: scan last 7 days for unclosed TODOs ---
echo ""
echo "=== CARRYOVER_TODOS ==="
found_carryover=0
for i in $(seq 1 7); do
  past_date=$(date -v-${i}d +%Y-%m-%d 2>/dev/null || date -d "$TODAY - $i days" +%Y-%m-%d 2>/dev/null)
  past_year=$(echo "$past_date" | cut -d- -f1)
  past_month=$(echo "$past_date" | cut -d- -f2)
  past_file="$NOTES_DIR/$past_year/$past_month/$past_date.md"

  if [[ -f "$past_file" ]]; then
    # Find TODOs and IN_PROGRESS that were never marked DONE in that file
    open_items=$(grep -E '^\- \[(TODO|IN_PROGRESS|BLOCKED)\]' "$past_file" 2>/dev/null)
    if [[ -n "$open_items" ]]; then
      found_carryover=1
      echo "--- $past_date ---"
      echo "$open_items"
      echo ""
    fi
  fi
done
if (( found_carryover == 0 )); then
  echo "(no carryover items found)"
fi

# --- Recent notes for context ---
echo ""
echo "=== RECENT_NOTES ==="
if [[ -f "$TODAY_FILE" ]]; then
  sed -n '/^## Notes$/,/^## /{ /^## /d; p; }' "$TODAY_FILE" | grep -v '^$'
else
  echo "(no notes today)"
fi
