
DROP TABLE IF EXISTS question;
DROP TABLE IF EXISTS question_type;
DROP TABLE IF EXISTS event;
DROP TABLE IF EXISTS answer;
-- DROP TABLE IF EXISTS question_answer;
-- DROP TABLE IF EXISTS day;
-- DROP TABLE IF EXISTS answers;
-- DROP TABLE IF EXISTS event_answer ;

SHOW TIMEZONE;
SET TIME ZONE 'Europe/Moscow';

CREATE TABLE question_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    notation_str VARCHAR(10) UNIQUE
);

-- DROP TABLE question;
CREATE TABLE question(
    pk SERIAL PRIMARY KEY,

    name VARCHAR(50) UNIQUE NOT NULL,
    order_by SERIAL,
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


CREATE TABLE event(
    pk SERIAL PRIMARY KEY,
    order_by SERIAL,
    name VARCHAR(50)
);


-- DROP TABLE IF EXISTS answer;
CREATE TABLE answer (
    pk SERIAL PRIMARY KEY ,
    date DATE
        DEFAULT now()::date,
    event_fk INTEGER
        REFERENCES event,
    question_fk INTEGER
        REFERENCES question,

    UNIQUE (date, question_fk),

    time TIME NULL, -- DEFAULT now()::time,
    text TEXT NULL,

    CONSTRAINT answer_is_time_for_event CHECK (
        CASE WHEN (event_fk IS NOT NULL)
            THEN string_is_time(text) = true END
    ),

    -- One of 'event_fk', 'question_fk' should be NULL
    CHECK (
        CASE WHEN (event_fk IS NOT NULL) THEN 1 ELSE 0 END +
        CASE WHEN (question_fk IS NOT NULL) THEN 1 ELSE 0 END = 1
    )
);

-- INSERT INTO answer (date, event_fk, question_fk, time) VALUES
--     ('2023-02-27', 1, NULL, '11:00:0'),
--     ('2023-02-27', 2, NULL, '11:00'),
--     ('2023-02-28', NULL, '1', '11:00')
--     ('2023-02-27', 4, NULL, now()),
--     ('2023-02-27', 5, NULL, now())
-- ;


-- New version OF 'question_answer' VIEW, by JOIN
SELECT date, q.name, text FROM answer AS a
--     LEFT JOIN event e ON e.pk = a.event_fk
    JOIN question q on q.pk = a.question_fk
WHERE
--     (a.date, q.name) = ('2023-02-25', 'walking')
--     a.date = '2023-02-25'
    a.date = now()::date
ORDER BY
    q.num_int;


-- Print all questions list
SELECT q.name, q.fulltext, q.suggested_answers_list, qt.notation_str FROM question_type AS qt
    JOIN question q
        ON qt.id = q.type_id;


----------- DELETE OPERATIONS -----------

-- Delete all ross with 'NaN'/NULL answer values
DELETE FROM question_answer
-- SELECT * FROM question_answer
    WHERE
        answer_text IS NULL
        OR answer_text = 'NaN';


-- DELETE FROM question_answer;

SELECT day_fk, question_fk, answer_text FROM question_answer
    WHERE
        (day_fk, question_fk) = ('2023-02-23', 'weight');

-- UPDATE question_answer SET (day_fk, answer_text) = ('2023-02-23', '66664')
UPDATE question_answer SET (answer_text) = ('66664')
    WHERE
        (day_fk, question_fk) = ('2023-02-23', 'weight');
