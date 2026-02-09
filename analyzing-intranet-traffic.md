---
name: analyzing-intranet-traffic
description: Analyze weekly intranet traffic and employee engagement. Use when looking at internal communication performance to identify popular content, user retention, and communication efficiency across departments or locations.
---

# Intranet Traffic Analysis

Automated analysis of internal communication and platform engagement.

## Input Requirements

Expects intranet analytics data in CSV format with these columns:

- **date**: Metric date
- **page_path**: URL/Path of the intranet page
- **department**: User department (if available via segments)
- **office_location**: User location (if available via segments)
- **active_users**: Number of unique users engaged
- **page_views**: Total page views
- **session_duration**: Average time spent on page/session (seconds)
- **bounce_rate**: Percentage of users who left after one page
- **clicks**: Clicks on internal news/banners
- **comments**: Number of comments on articles
- **shares**: Number of internal shares/forwards

## Data Quality Check

1. Check for missing values in `department` or `office_location` (fallback to "Unassigned").
2. Verify total `active_users` matches expected employee headcount (identify access issues).
3. Flag anomalies (e.g., extremely high `session_duration` which might indicate tab-hanging).

## Engagement Analysis

Calculate per page or department:

- **Engagement Rate** = active_users / total_headcount × 100
- **Interaction Rate** = (clicks + comments) / active_users × 100

Compare to organizational benchmarks. If not provided, use these internal standards:

| Page Type | Target Engagement | Target Interaction |
|-----------|-------------------|--------------------|
| CEO_Updates | 85% | 15% |
| HR_Benefits | 60% | 5% |
| IT_Support | 40% | 20% |
| General_News | 50% | 3% |

## Efficiency & Adoption Analysis

Calculate per segment:

- **Stickiness Ratio** = daily_active_users / monthly_active_users
- **Content ROI** = page_views / effort_hours (if effort data is available)
- **Reading Depth** = (session_duration / estimated_reading_time) × 100
  - Unless specified, use:
    - **Estimated Reading Time**: 500 words per 2 minutes

Compare to targets:

- **Target Stickiness**: 0.3 minimum (regular daily usage)
- **Min Reading Depth**: 70% for mandatory communications

## Output Format

Present results as tables with status indicators:

**Engagement Analysis Table:**
| Department | Engagement Actual | Target | Engagement Diff | Interaction Actual | Target | Interaction Diff |

**User Behavior Table:**
| Page Path | Stickiness | Status | Reading Depth | Status | Bounce Rate | Status |

Status indicators:

- Engagement: "[OK] Reached" if >= target, "[X] Below" if < target
- Stickiness: "[OK] High" if >= 0.3, "[X] Low" if < 0.3
- Reading Depth: "[OK] Read" if >= 70%, "[X] Skimmed" if < 70%

Follow each table with brief interpretation highlighting the most engaged departments and content gaps.

## Strategic Recommendations

If user asks for content strategy, refer to `strategies/internal_comm_best_practices.md` for guidance on timing, formats (video vs text), and notification threshold rules.
