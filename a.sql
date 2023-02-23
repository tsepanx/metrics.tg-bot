
DROP TABLE IF EXISTS question_answer;
DROP TABLE IF EXISTS day;
DROP TABLE IF EXISTS question;
DROP TABLE IF EXISTS question_type;

CREATE TABLE question_type (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    notation_str VARCHAR(10) UNIQUE
);

-- ALTER TABLE question_type
--     ADD COLUMN
--         IF NOT EXISTS
--         notation_str VARCHAR(10) UNIQUE;

-- Examples of ALTERing column
-- ALTER TABLE question_type ALTER COLUMN notation_str TYPE VARCHAR(10);
-- ALTER TABLE question_type ADD CONSTRAINT UNIQUE (notation_str);
-- ALTER TABLE question_type ALTER COLUMN notation_str SET DEFAULT 'default_val';


CREATE TABLE question(
--     pk SERIAL PRIMARY KEY,
    num_int SERIAL,
    name VARCHAR(50) PRIMARY KEY UNIQUE NOT NULL,
    fulltext TEXT DEFAULT 'Question fulltext',
    suggested_answers_list TEXT NOT NULL DEFAULT '[,]',
    type_id INTEGER DEFAULT 1 NOT NULL
        REFERENCES question_type

--     CONSTRAINT fk_type_id
--         FOREIGN KEY(type_id)
--         REFERENCES question_type(id)
);

-- DROP TABLE IF EXISTS day;
CREATE TABLE day(
    date DATE PRIMARY KEY
);

CREATE TABLE question_answer(
    day_fk DATE REFERENCES day(date),
    question_fk VARCHAR REFERENCES question(name),

    answer_text TEXT NOT NULL DEFAULT '',
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


INSERT INTO day(date)
VALUES
    ('2023-02-22'),
    ('2023-02-23'),
    ('2023-02-24');


INSERT INTO question_type(id, name, notation_str)
VALUES
    (0, 'plain', ''),
    (1, 'int', '(D)'),
    (2, 'binary', '(0/1)'),
    (3, 'hours', '(H)');


INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('sleep_1_start', '`(H)` Отбой (время)', '{22:00,23:00,00:00,01:00}', 3);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('sleep_2_end', '`(H)` Подъем (время)', '{08:00,09:00,10:00,11:00,12:00}', 3);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('sleep_hrs', '`(H)` Sleep hours (hours) (h-w-gt3)', '{7.5,8,8.5,9}', 3);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('sleep_score', '`(0-100)` Sleep score (h-w-gt3)', '{50,75,100}', 1);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('steps_cnt', '`(D)` Steps count  (h-w-gt3)', '{6000,8000,10000,20000}', 1);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('hrs_active', '`(D)` Hours active  (h-w-gt3)', '{0,1,2,6,8,12}', 1);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('mins_activity', '`(H)` Minutes activity (h-w-gt3)', '{00:00,00:30,01:00,01:30}', 3);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('sport_trainings', '`(H)` Спорт. тренировки (часы)?', '{00:00,00:30,01:00,01:30}', 3);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('walking', '(H) Прогулка (часы)?', '{00:00,00:30,01:00,01:30}', 3);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('oatmeal_eat', '`(0/1)` Овсянка?', '{Да,Нет}', 2);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('meat_eat', '`(0/1)` Мясо?', '{Да,Нет}', 2);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('fish_eat', '`(0/1)` Рыба?', '{Да,Нет}', 2);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('vegetables_eat', '`(Grams)` Овощи?', '{0,50,100,150}', 1);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('nuts_eat', '`(Grams)` Орехи?', '{0,40,80,120}', 1);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('sugar_eat', '`(0-10)` Сладкое?', '{0,1,2,3,4,5,6,7,8,9,10}', 1);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('x_big', 'X?', '{1,0}', 2);
INSERT INTO public.question(name,fulltext,suggested_answers_list, type_id) VALUES ('x_small', '(x)?', '{1,0}', 2);


-- INSERT INTO question_answer(day_fk, question_fk, answer_text)
-- VALUES
--     ('2023-02-22', 'walking', 'Answer on walking yesterday ;)'),
--     ('2023-02-23', 'walking', '6000');

-- SELECT * FROM question
--     JOIN question_type qt
--         ON question.type_id = qt.id;

-- Print all questions list
SELECT q.name, qt.name, q.num_int, q.fulltext FROM question_type AS qt
    JOIN question q
        ON qt.id = q.type_id;

-- Show all answers for given day, sorted by q.num_int
SELECT qa.day_fk, qa.question_fk, qa.answer_text FROM question_answer AS qa
    JOIN question q on q.name = qa.question_fk
    WHERE
        day_fk = '2023-02-21'
    ORDER BY day_fk, q.num_int;

-- Delete all 'NaN' values
DELETE FROM question_answer
       WHERE
        answer_text = 'NaN';