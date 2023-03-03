


ALTER TABLE event ADD UNIQUE (name);


-- DROP TABLE tg_user;
CREATE TABLE tg_user (
--     pk SERIAL PRIMARY KEY,
    user_id SERIAL PRIMARY KEY
);

-- DROP TABLE lasting_event;
CREATE TABLE lasting_event (
    pk SERIAL PRIMARY KEY,

    user_id INTEGER
        REFERENCES tg_user,

    order_by SERIAL,
    name VARCHAR(50) UNIQUE,

    is_started BOOLEAN
        NOT NULL DEFAULT True,

    is_activated BOOLEAN
        NOT NULL DEFAULT True
);

ALTER TABLE question ADD COLUMN
    user_id INTEGER
        REFERENCES tg_user;

ALTER TABLE event ADD COLUMN
    user_id INTEGER
        REFERENCES tg_user;

ALTER TABLE answer ADD COLUMN
    lasting_event_fk INTEGER
        REFERENCES lasting_event;

ALTER TABLE answer DROP CONSTRAINT answer_check;
ALTER TABLE answer ADD CHECK (
    CASE WHEN (event_fk IS NOT NULL) THEN 1 ELSE 0 END +
    CASE WHEN (question_fk IS NOT NULL) THEN 1 ELSE 0 END +
    CASE WHEN (lasting_event_fk IS NOT NULL) THEN 1 ELSE 0 END = 1
);

ALTER TABLE answer RENAME CONSTRAINT answer_check TO single_fk_not_null;

ALTER TABLE answer DROP CONSTRAINT answer_is_time_for_event;
ALTER TABLE answer ADD CONSTRAINT answer_is_time_for_event CHECK (
    ( (event_fk IS NOT NULL) AND (time IS NOT NULL) )
        OR
    ( (answer.lasting_event_fk IS NOT NULL) AND (time IS NOT NULL) )
        OR
    ( (event_fk IS NULL) )
);

