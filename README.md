## `Metrics.tg-bot`

### Refactoring TODO's

- Move `conversations` strings to **constants** 

### TODO for `Tomorrow`

- [ ] Visualise Inline button select with emoji 
- [ ] Add ability to create `event` answer
- [x] Find ability to select in entities names

---
- [x] Display events as {index - time, value - tuple (event_name, text)}
- Involve `groups`
- [x] -> Optimize number of `SQL` requests
  - Check whether any `table` changed to reload "db attrs"
  - Check output requests, fix duplicate requests
- [x] `DB` support (`PosgreSQL`)
- [x] `/ask missing`
- ~~Store `questions_objects` as file~~
- [X] Save `answers_df` in `State`

#### Commands
- `/add new_name; [0, 1, 2]; lambda x: x * 50`
- `/rename 0 new_name`
  - `/rename old_name new_name`
- `/drop 0`; `/drop name`
- `/deactivate 0`; `/deactivate name`
