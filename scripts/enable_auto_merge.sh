#!/bin/bash

# Enable auto-merge on all open PRs matching a pattern
# Usage: ./scripts/enable_auto_merge.sh [pattern]
# Example: ./scripts/enable_auto_merge.sh "pcon-864"

PATTERN="${1:-pcon-864}"

echo "🔍 Finding open PRs with branches containing: $PATTERN"
echo ""

# Get all open PRs matching the pattern
prs=$(gh pr list --state open --json number,headRefName,title,url --jq ".[] | select(.headRefName | contains(\"$PATTERN\")) | [.number, .headRefName, .title, .url] | @tsv")

if [ -z "$prs" ]; then
    echo "❌ No open PRs found matching pattern: $PATTERN"
    exit 0
fi

total=$(echo "$prs" | wc -l | xargs)
echo "Found $total matching PR(s)"
echo ""

# Process each PR
while IFS=$'\t' read -r pr_number branch_name title pr_url; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "PR #$pr_number: $title"
    echo "Branch: $branch_name"
    echo "URL: $pr_url"
    echo ""

    # Check current merge status
    echo "📊 Checking merge status..."
    merge_info=$(gh pr view "$pr_number" --json mergeable,mergeStateStatus,autoMergeRequest,statusCheckRollup,reviewDecision)

    mergeable=$(echo "$merge_info" | jq -r '.mergeable')
    merge_state=$(echo "$merge_info" | jq -r '.mergeStateStatus')
    auto_merge_enabled=$(echo "$merge_info" | jq -r '.autoMergeRequest != null')
    review_decision=$(echo "$merge_info" | jq -r '.reviewDecision')

    # Parse status checks
    pending_checks=$(echo "$merge_info" | jq -r '[.statusCheckRollup[] | select(.state == "PENDING") | .name] | join(", ")')
    failing_checks=$(echo "$merge_info" | jq -r '[.statusCheckRollup[] | select(.conclusion != "SUCCESS" and .conclusion != "NEUTRAL" and .conclusion != "SKIPPED" and .conclusion != null and .state != "PENDING") | .name] | join(", ")')

    echo "  Mergeable: $mergeable"
    echo "  Merge State: $merge_state"
    echo "  Auto-merge: $auto_merge_enabled"
    echo "  Review Status: $review_decision"

    if [ -n "$pending_checks" ]; then
        echo "  ⏳ Pending checks: $pending_checks"
    fi

    if [ -n "$failing_checks" ]; then
        echo "  ❌ Failing checks: $failing_checks"
    fi

    echo ""

    # Check if branch needs updating
    needs_update=false
    if [ "$merge_state" = "BEHIND" ] || [ "$merge_state" = "DIRTY" ]; then
        needs_update=true
        echo "🔄 Branch is behind base - updating..."
        if gh pr merge "$pr_number" --update-branch 2>&1; then
            echo "✓ Branch updated successfully"
            # Wait a moment for GitHub to process
            sleep 2
            # Re-fetch merge status
            merge_info=$(gh pr view "$pr_number" --json mergeable,mergeStateStatus,autoMergeRequest,statusCheckRollup,reviewDecision)
            merge_state=$(echo "$merge_info" | jq -r '.mergeStateStatus')
            echo "  New merge state: $merge_state"
        else
            echo "⚠ Could not update branch automatically"
        fi
        echo ""
    fi

    # Enable auto-merge if not already enabled
    if [ "$auto_merge_enabled" = "true" ]; then
        echo "✓ Auto-merge already enabled"

        # Explain why it's not merging if blocked
        if [ "$mergeable" = "CONFLICTING" ]; then
            echo "⚠ Cannot merge: PR has merge conflicts"
        elif [ "$merge_state" = "BLOCKED" ]; then
            if [ "$review_decision" = "REVIEW_REQUIRED" ]; then
                echo "⚠ Waiting for required reviews"
            elif [ "$review_decision" = "CHANGES_REQUESTED" ]; then
                echo "⚠ Changes requested in review"
            elif [ -n "$failing_checks" ]; then
                echo "⚠ Blocked by failing checks"
            elif [ -n "$pending_checks" ]; then
                echo "⏳ Waiting for checks to complete"
            else
                echo "⚠ Blocked by branch protection rules"
            fi
        elif [ "$merge_state" = "BEHIND" ] || [ "$merge_state" = "DIRTY" ]; then
            echo "⚠ Branch needs to be updated with base (should have been updated above)"
        elif [ -n "$pending_checks" ]; then
            echo "⏳ Will merge when checks complete"
        else
            echo "✓ Ready to merge"
        fi
    else
        echo "🔄 Enabling auto-merge..."
        if gh pr merge "$pr_number" --auto --squash 2>&1; then
            echo "✓ Auto-merge enabled (squash strategy)"

            # Check if there are blockers
            if [ "$mergeable" = "CONFLICTING" ]; then
                echo "⚠ Cannot merge yet: PR has merge conflicts"
            elif [ "$merge_state" = "BEHIND" ] || [ "$merge_state" = "DIRTY" ]; then
                echo "⚠ Branch needs to be updated (will retry on next run)"
            elif [ "$review_decision" = "REVIEW_REQUIRED" ]; then
                echo "⏳ Will merge after required reviews"
            elif [ "$review_decision" = "CHANGES_REQUESTED" ]; then
                echo "⚠ Changes requested - needs resolution"
            elif [ -n "$failing_checks" ]; then
                echo "⚠ Will merge after failing checks are fixed"
            elif [ -n "$pending_checks" ]; then
                echo "⏳ Will merge when checks complete"
            else
                echo "✓ Will merge automatically"
            fi
        else
            echo "❌ Failed to enable auto-merge"
        fi
    fi

    echo ""
done <<< "$prs"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Processed $total PR(s)"
