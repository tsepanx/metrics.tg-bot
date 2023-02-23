
DROP TABLE IF EXISTS question_answer;
DROP TABLE IF EXISTS day;
DROP TABLE IF EXISTS question;
DROP TABLE IF EXISTS question_type;

CREATE TABLE question_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    notation_str VARCHAR(10) UNIQUE
);


-- Examples of ALTERing column
-- ALTER TABLE question_type ADD COLUMN IF NOT EXISTS notation_str VARCHAR(10) UNIQUE;
-- ALTER TABLE question_type ALTER COLUMN notation_str TYPE VARCHAR(10);
-- ALTER TABLE question_type ADD CONSTRAINT UNIQUE (notation_str);
-- ALTER TABLE question_type ALTER COLUMN notation_str SET DEFAULT 'default_val';


CREATE TABLE question(
--     pk SERIAL PRIMARY KEY,
    name VARCHAR(50)
            PRIMARY KEY,
    num_int SERIAL,
    fulltext TEXT
        DEFAULT num_int,
    suggested_answers_list TEXT
        NOT NULL
        DEFAULT '[,]',
    type_id INTEGER
        DEFAULT 1
        NOT NULL
        REFERENCES question_type
            ON DELETE SET DEFAULT,
    is_activated BOOLEAN
        DEFAULT False
        NOT NULL

--     CONSTRAINT fk_type_id
--         FOREIGN KEY(type_id)
--         REFERENCES question_type(id)
);

-- DROP TABLE IF EXISTS day;
CREATE TABLE day(
    date DATE PRIMARY KEY
);

DROP TABLE question_answer;
CREATE TABLE question_answer(
    day_fk DATE REFERENCES day(date),
    question_fk VARCHAR REFERENCES question(name),

    answer_text TEXT,
    CONSTRAINT pk PRIMARY KEY (day_fk, question_fk)
);

-- ALTER TABLE question
--     ADD CONSTRAINT fk_question_type
--         FOREIGN KEY (type_id)
--         REFERENCES question_type(id);

-- ALTER TABLE question ALTER COLUMN suggested_answers_list TYPE VARCHAR(100);
-- ALTER TABLE question DROP COLUMN suggested_answers_list;
-- ALTER TABLE question ALTER COLUMN suggested_answers_list SET DEFAULT '[,]';
-- ALTER TABLE question ADD COLUMN suggested_answers_list TEXT NOT NULL DEFAULT '[,]';


INSERT INTO day(date) VALUES ('2023-02-20');
INSERT INTO day(date) VALUES ('2023-02-21');
INSERT INTO day(date) VALUES ('2023-02-22');
INSERT INTO day(date) VALUES ('2023-02-23');
INSERT INTO day(date) VALUES ('2023-02-24');


INSERT INTO question_type(id, name, notation_str)
VALUES
    (0, 'plain', ''),
    (1, 'int', '(D)'),
    (2, 'binary', '(0/1)'),
    (3, 'hours', '(H)');



-- Print all questions list
SELECT q.name, qt.notation_str, q.fulltext FROM question_type AS qt
    JOIN question q
        ON qt.id = q.type_id;

-- Show all answers for given day, sorted by q.num_int
SELECT qa.day_fk, qa.question_fk, qa.answer_text FROM question_answer AS qa
    JOIN question q on q.name = qa.question_fk
    WHERE
        day_fk = '2023-02-21'
    ORDER BY day_fk, q.num_int;


-- Delete all 'NaN' values
-- DELETE FROM question_answer
SELECT * FROM question_answer
       WHERE
--         answer_text = 'NaN'
            answer_text IS NULL;