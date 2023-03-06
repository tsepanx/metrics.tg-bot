
DROP TABLE IF EXISTS question CASCADE ;
DROP TABLE IF EXISTS question_type CASCADE ;
DROP TABLE IF EXISTS event CASCADE ;
DROP TABLE IF EXISTS event_text_prefix CASCADE ;
DROP TABLE IF EXISTS lasting_event CASCADE ;
DROP TABLE IF EXISTS answer CASCADE ;
DROP TABLE IF EXISTS tg_user CASCADE ;
DROP TYPE IF EXISTS event_type CASCADE ;
-- DROP TABLE IF EXISTS question_answer;
-- DROP TABLE IF EXISTS day;
-- DROP TABLE IF EXISTS answers;
-- DROP TABLE IF EXISTS event_answer ;

SHOW TIMEZONE;
SET TIME ZONE 'Europe/Moscow';

CREATE TABLE tg_user (
    user_id SERIAL PRIMARY KEY
);

-- CREATE TABLE question_type (
--     pk SERIAL PRIMARY KEY,
--     name VARCHAR(50) UNIQUE NOT NULL,
--     notation_str VARCHAR(50) UNIQUE
-- );

-- DROP TABLE question;
CREATE TABLE question(
    pk SERIAL PRIMARY KEY,

    user_id INTEGER
        REFERENCES tg_user,

    name VARCHAR(50) UNIQUE NOT NULL,
    order_by SERIAL,
    fulltext TEXT
        DEFAULT '',
    choices_list VARCHAR(50)[] NULL,
    type_id INTEGER
        DEFAULT 1
        NOT NULL,
--         REFERENCES question_type
--             ON DELETE SET DEFAULT,
    is_activated BOOLEAN
        DEFAULT True
        NOT NULL
);


-- DROP TABLE event;

CREATE TYPE event_type AS ENUM ('Single', 'Durable');

CREATE TABLE event(
    pk SERIAL PRIMARY KEY,

    user_id INTEGER
        REFERENCES tg_user,

    name VARCHAR(50) UNIQUE,
    "type" event_type
        DEFAULT 'Single',
    is_activated BOOLEAN
        NOT NULL DEFAULT True,

    order_by SERIAL
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
--     lasting_event_fk INTEGER
--         REFERENCES lasting_event,

    UNIQUE (date, question_fk),

    time TIME NULL, -- DEFAULT now()::time,
    text TEXT NULL,

    CONSTRAINT answer_is_time_for_event CHECK (
        ((event_fk IS NOT NULL) AND (time IS NOT NULL))  OR
--         ((answer.lasting_event_fk IS NOT NULL) AND (time IS NOT NULL)) OR
        (event_fk IS NULL)
    ),

    -- One of 'event_fk', 'question_fk' should be NULL
    CONSTRAINT single_fk_not_null CHECK (
        CASE WHEN (event_fk IS NOT NULL) THEN 1 ELSE 0 END +
        CASE WHEN (question_fk IS NOT NULL) THEN 1 ELSE 0 END
--         CASE WHEN (lasting_event_fk IS NOT NULL) THEN 1 ELSE 0 END
        = 1
    )
);


SELECT date, time, e.name, text FROM answer
    LEFT OUTER JOIN event e on answer.event_fk = e.pk
WHERE event_fk IS NOT NULL
ORDER BY date, time;

SELECT * FROM answer WHERE
(SELECT name FROM event WHERE event.name = event_fk);

-- (SELECT name FROM event WHERE event.name = event_fk);

SELECT *, replace(name, 'food_eat', 'food_intake') FROM event ;

UPDATE event SET name = REPLACE(name, 'foodddd', 'food')
    WHERE name LIKE 'foodddd%';
