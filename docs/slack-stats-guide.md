# 📊 SBM Stats Command Guide

## Basic Commands

• `/sbm-stats` → Stats for the last 7 days (default)
• `/sbm-stats all` → All-time stats since project inception
• `/sbm-stats day` → Last 24 hours
• `/sbm-stats week` → Last 7 days
• `/sbm-stats month` → Last 30 days

---

## Custom Periods

• `/sbm-stats 14` → Last 14 days
• `/sbm-stats 90` → Last 90 days

---

## Specific Month (MM/YY)

• `/sbm-stats 12/25` → Month of December 2025
• `/sbm-stats 1/26` → Month of January 2026

---

## Specific Day (MM/DD/YY)

• `/sbm-stats 1/15/26` → January 15, 2026
• `/sbm-stats 12/25/25` → December 25, 2025

---

## Date Ranges

• `/sbm-stats 1/1/26 to 1/15/26` → Jan 1 - Jan 15, 2026
• `/sbm-stats 12/1/25 to 12/31/25` → Full December 2025
• `/sbm-stats 14 1/1/26` → 14 days starting Jan 1, 2026

---

## Filter by User

• `/sbm-stats nate-hart-di` → Stats for user (last 7 days)
• `/sbm-stats month nate-hart-di` → User stats for last 30 days
• `/sbm-stats 1/26 nate-hart-di` → User stats for January 2026

---

## Top Contributors

• `/sbm-stats top 5` → Top 5 contributors (all time)
• `/sbm-stats month top 10` → Top 10 for last 30 days

---

## Tips

• Usernames are case-insensitive and support partial matching
• Date formats accept single or double digits: 1/26 = 01/26
• Combine period + user: `/sbm-stats week nate-hart-di`
