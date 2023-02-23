
-- Show all answers for given day, sorted by q.num_int
SELECT qa.question_fk, qa.answer_text FROM question_answer AS qa
    JOIN question q on q.name = qa.question_fk
    WHERE
        qa.day_fk = '2023-02-21'
    ORDER BY qa.day_fk, q.order_int;