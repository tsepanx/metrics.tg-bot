
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

CREATE TABLE tg_user (
    user_id SERIAL PRIMARY KEY
);

CREATE TABLE question_type (
    pk SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    notation_str VARCHAR(10) UNIQUE
);

-- DROP TABLE question;
CREATE TABLE question(
    pk SERIAL PRIMARY KEY,

    user_id INTEGER
        REFERENCES tg_user,

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
);


-- DROP TABLE event;
CREATE TABLE event(
    pk SERIAL PRIMARY KEY,

    user_id INTEGER
        REFERENCES tg_user,

    order_by SERIAL,
    name VARCHAR(50) UNIQUE,
    is_activated BOOLEAN
        NOT NULL DEFAULT True
);

CREATE TABLE lasting_event(
    pk SERIAL PRIMARY KEY,

    user_id INTEGER
        REFERENCES tg_user,

    order_by SERIAL,
    name VARCHAR(50) UNIQUE,
    is_activated BOOLEAN
        NOT NULL DEFAULT True,

    is_started BOOLEAN
        NOT NULL DEFAULT False
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
    lasting_event_fk INTEGER
        REFERENCES lasting_event,

    UNIQUE (date, question_fk),

    time TIME NULL, -- DEFAULT now()::time,
    text TEXT NULL,

    CONSTRAINT answer_is_time_for_event CHECK (
        ((event_fk IS NOT NULL) AND (time IS NOT NULL))  OR
        ((answer.lasting_event_fk IS NOT NULL) AND (time IS NOT NULL)) OR
        (event_fk IS NULL)
    ),

    -- One of 'event_fk', 'question_fk' should be NULL
    CONSTRAINT single_fk_not_null CHECK (
        CASE WHEN (event_fk IS NOT NULL) THEN 1 ELSE 0 END +
        CASE WHEN (question_fk IS NOT NULL) THEN 1 ELSE 0 END +
        CASE WHEN (lasting_event_fk IS NOT NULL) THEN 1 ELSE 0 END = 1
    )
);


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