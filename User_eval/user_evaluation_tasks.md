# User Evaluation Tasks

This document contains 3 user evaluation tasks to assess the retrieval effectiveness of the AFURI menu search system.

## Evaluation Instructions

- **Evaluation Criteria**: After completing each task, please rate the relevance of the top 10 results
  - 👍 **Useful**: Results are highly relevant to the query
  - 👎 **Not useful**: Results are irrelevant or have low relevance to the query

- **Evaluation Focus**:
  - Relevance of results
  - Reasonableness of ranking
  - Accuracy of cross-language search
  - Accuracy of semantic understanding

---

## Task 1: Keyword Combination Search

### Task Description
Test the system's ability to handle English keyword combination searches. Using two keywords "yuzu" and "ramen" to search, the system should be able to find menu items that contain both keywords or are semantically related.

### Query
```
yuzu ramen
```

### Expected Results
- Should find ramen products containing yuzu (citrus fruit)
- Examples: Yuzu salt ramen, Yuzu soy sauce ramen, etc.
- Results should be related to both yuzu and ramen

### Evaluation Points
1. **Keyword Matching Accuracy**: Whether results containing both "yuzu" and "ramen" are found
2. **Result Relevance**: Whether all returned results are yuzu-related ramen products
3. **Ranking Reasonableness**: Whether the most relevant results (containing both yuzu and ramen) are ranked first

### Evaluation Steps
1. Enter in the search box: `yuzu ramen`
2. Review the top 10 returned results
3. Click 👍 or 👎 for each result
4. Record the following information:
   - Relevance of the top 3 results
   - Whether expected yuzu ramen products are found
   - Whether the ranking is reasonable

---

## Task 2: Price Filter with Tag Filter

### Task Description
Test the system's price filtering and tag filtering capabilities. First search for items priced below 1000 yen, then filter by the "noodles" tag to find noodles-related items.

### Query
```
prices below 1000 JPY
```

### Filter Conditions
1. **Price Range**: < ¥1,000
2. **Tag**: noodles

### Expected Results
- Should find items priced below 1000 yen with the "noodles" tag
- Results should satisfy both conditions: price < 1000 yen and tag contains "noodles"
- Examples: Various noodle products priced below 1000 yen

### Evaluation Points
1. **Price Filter Accuracy**: Whether all results are priced below 1000 yen
2. **Tag Filter Accuracy**: Whether all results contain the "noodles" tag
3. **Combined Filter Functionality**: Whether price filtering and tag filtering work simultaneously
4. **Result Relevance**: Whether returned results are all noodles-related and meet the price requirement

### Evaluation Steps
1. Enter in the search box: `1000元以下的`
2. Click the price filter and select "< ¥1,000"
3. Click the tag filter and select "#noodles"
4. Review the top 10 returned results
5. Click 👍 or 👎 for each result
6. **Important**: Click the top 3 results to view detail page content and verify information accuracy
7. Record the following information:
   - Whether all results are priced below 1000 yen
   - Whether all results contain the "noodles" tag
   - Whether the ranking is reasonable
   - Whether the detail page content is accurate

---

## Task 3: Cross-Language Semantic Search with Content Review

### Task Description
Test the system's cross-language semantic understanding capability for single-character Japanese queries. Using the Japanese character "豚" (pork) to search, the system should be able to find menu items containing pork, chicken, meat, and related content. **Important**: Need to click on results to view detail page content and assess the accuracy and completeness of the content.

### Query
```
豚
```

### Expected Results
- Should find menu items related to pork
- Examples: Ramen or dishes containing chashu (char siu), pork, meat, etc.
- May also include other meat-related menu items

### Evaluation Points
1. **Cross-Language Semantic Matching Accuracy**: Whether the Japanese "豚" correctly matches English "pork" related content
2. **Result Relevance**: Whether returned results are related to pork
3. **Ranking Reasonableness**: Whether the most relevant results are ranked first
4. **Content Accuracy**: Whether the content displayed on the detail page is accurate and complete

### Evaluation Steps
1. Enter in the search box: `豚`
2. Review the top 10 returned results
3. **Important**: Click the top 5 results to enter the detail page and view complete content
4. Click 👍 or 👎 for each result
5. Record the following information:
   - Relevance of the top 3 results
   - Whether expected pork-related content is found
   - Whether the ranking is reasonable
   - Whether the detail page content is accurate and complete
   - Whether the detail page contains expected pork-related information

---

## Evaluation Metrics Summary

### Overall Assessment

1. **Keyword Combination Search Capability** (Based on Task 1)
   - Score: _____ / 5
   - Comments: _________________________________

2. **Price Filtering and Tag Filtering Capability** (Based on Task 2)
   - Score: _____ / 5
   - Comments: _________________________________

3. **Cross-Language Search and Content Accuracy** (Based on Task 3)
   - Score: _____ / 5
   - Comments: _________________________________

### Overall Score

- **Overall System Performance**: _____ / 5
- **Most Satisfying Feature**: _________________________________
- **Areas for Improvement**: _________________________________
- **Other Suggestions**: _________________________________

---

## Evaluation Completion Time

- Start Time: __________
- End Time: __________
- Total Duration: __________ minutes

---

**Thank you for your participation!**
