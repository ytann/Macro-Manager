# Async Item-by-Item Resolution Plan

## Goal
Transition from monolithic meal resolution to a granular, item-by-item asynchronous pipeline to avoid server timeouts and improve UX.

## Implementation Details

### 1. Backend: Item-Level Tracking
- **Status Tracking**: Introduce a mechanism (DB table or cache) to track the status (`pending`, `completed`, `failed`) of each individual item within a `meal_id`.
- **Granular Resolution**: Modify `_process_and_save_meal` to resolve items sequentially or in parallel.
- **Per-Item Retries**: Assign a dedicated retry budget (e.g., 15 attempts) per item rather than a collective budget for the whole meal.

### 2. API: Progress-Aware Status
- **Enhanced Endpoint**: Update `/log/status/{meal_id}` to return a progress object:
  ```json
  {
    "status": "processing",
    "completed": 1,
    "total": 2
  }
  ```

### 3. Frontend: Dynamic Progress UI
- **Item Progress**: Update the loader in `app/frontend.py` to display "Processing item X of Y..."
- **Visual Feedback**: Provide real-time updates as items are resolved, reducing perceived latency.
- **Extended Time Budget**: Effectively increase total resolution time by distributing the retry budget across all items.

## Benefits
- **Resilience**: A single "hard-to-find" item will not block the resolution of other items.
- **Transparency**: User sees exact progress instead of a generic attempt counter.
- **Stability**: Reduces likelihood of request timeouts by breaking one large task into smaller, trackable units.
