



INSERT INTO question_type VALUES
    (0, 'text', '[Text]'),
    (1, 'int', '[Decimal]'),
    (2, 'binary', '[0/1 Binary]'),
    (3, 'time', '[Time (hours)]'),
    (4, 'choice', '[Choice]')
;

INSERT INTO event (name, type) VALUES
    ('sleep', 'Durable'),
    ('sport_training', 'Durable'),
    ('walking', 'Durable')
;

INSERT INTO question (name, fulltext, choices_list, type_id) VALUES
    ('weight', '', '{65,70,75}', 1),
    ('steps_cnt', '', '{6000,8000,1000}', 1)
;