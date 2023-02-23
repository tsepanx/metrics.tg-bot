
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


-- DROP TABLE question;

CREATE TABLE question(
--     pk SERIAL PRIMARY KEY,
    name VARCHAR(50) PRIMARY KEY,
    num_int SERIAL,
    fulltext TEXT
        DEFAULT '',
    suggested_answers_list VARCHAR(50)[],
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
    date DATE PRIMARY KEY,
    display BOOLEAN
        DEFAULT True
        NOT NULL
);

-- DROP TABLE question_answer;
CREATE TABLE question_answer(
    day_fk DATE
        REFERENCES day(date),
    question_fk VARCHAR
        REFERENCES question(name),
    CONSTRAINT pk PRIMARY KEY (day_fk, question_fk),

    answer_text TEXT
);

-- ALTER TABLE question
--     ADD CONSTRAINT fk_question_type
--         FOREIGN KEY (type_id)
--         REFERENCES question_type(id);


-- Show all answers for given day, sorted by q.num_int
SELECT qa.question_fk, qa.answer_text FROM question_answer AS qa
    JOIN question q on q.name = qa.question_fk
    WHERE
        qa.day_fk = '2023-02-21'
    ORDER BY qa.day_fk, q.num_int;


-- Delete all ross with 'NaN'/NULL answer values
DELETE FROM question_answer
-- SELECT * FROM question_answer
    WHERE
        answer_text IS NULL
        OR answer_text = 'NaN';


-- DELETE FROM question_answer;

-- SELECT day_fk, question_fk FROM question_answer;