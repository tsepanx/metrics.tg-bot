
-- Examples of ALTERing column
-- ALTER TABLE question_type ADD COLUMN IF NOT EXISTS notation_str VARCHAR(10) UNIQUE;
-- ALTER TABLE question_type ALTER COLUMN notation_str TYPE VARCHAR(10);
-- ALTER TABLE question_type ADD CONSTRAINT UNIQUE (notation_str);
-- ALTER TABLE question_type ALTER COLUMN notation_str SET DEFAULT 'default_val';



-- ALTER TABLE <table_name> DROP CONSTRAINT <table_name>_pkey;
ALTER TABLE question_answer DROP CONSTRAINT question_answer_question_fk_fkey;
ALTER TABLE question DROP CONSTRAINT question_pkey;
-- ALTER TABLE answer DROP CONSTRAINT answer_question_fk_fkey;

-- ALTER TABLE ONLY public.question_answer
--     ADD CONSTRAINT question_answer_question_fk_fkey FOREIGN KEY (question_fk) REFERENCES public.question(name);

ALTER TABLE question ADD COLUMN
    pk SERIAL PRIMARY KEY;

ALTER TABLE question ADD CONSTRAINT question_name_uniq UNIQUE (name);
ALTER TABLE question ALTER COLUMN name SET NOT NULL;

-- ALTER TABLE ONLY question_answer
--     ADD CONSTRAINT question_answer_question_fk_fkey
--         FOREIGN KEY (question_fk)
--             REFERENCES public.question(name);

--- question_answer fk(q.name) -> fk(q.pk)

ALTER TABLE question_answer ADD COLUMN
    question_fk_2 INTEGER
        REFERENCES question(pk);

UPDATE question_answer
    SET question_fk_2 = q.pk
FROM question q
    WHERE q.name = question_answer.question_fk;

ALTER TABLE question_answer DROP COLUMN question_fk;
ALTER TABLE question_answer RENAME COLUMN question_fk_2 TO question_fk;

---

--- Now create table 'answers'

--- answer fk(q.name) -> fk(q.pk) (ALREADY)

--- Insert 'question_answer' -> 'answer'

INSERT INTO answer (date, question_fk, text)
    SELECT day_fk::date, question_fk, answer_text FROM question_answer;



-- New version OF 'question_answer' VIEW, by JOIN
SELECT date, q.name, text FROM answer AS a
--     LEFT JOIN event e ON e.pk = a.event_fk
    JOIN question q on q.pk = a.question_fk
WHERE
--     (a.date, q.name) = ('2023-02-25', 'walking')
--     a.date = '2023-02-25'
    a.date = now()::date
ORDER BY
    q.order_by;


SELECT "answer"."question_fk", "answer"."text" FROM "answer"
    JOIN "question" ON "answer"."question_fk" = "question"."pk"
WHERE (question_fk) IN (1, 2, 3) AND (is_activated) IN (True)
ORDER BY "question".order_by;



-- Print all questions list
SELECT * FROM question q
    JOIN question_type qt
        ON "q"."type_id" = qt.pk;

SELECT date from answer
GROUP BY date
ORDER BY date;

SELECT * FROM "answer" a
    LEFT JOIN "question" q ON a."question_fk" = q."pk"
    LEFT JOIN "event" e ON a."event_fk" = e."pk"
ORDER BY a."date";