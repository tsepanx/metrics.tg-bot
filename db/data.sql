

INSERT INTO day(date) VALUES ('2023-02-20');
INSERT INTO day(date) VALUES ('2023-02-21');
INSERT INTO day(date) VALUES ('2023-02-22');
INSERT INTO day(date) VALUES ('2023-02-23');
INSERT INTO day(date) VALUES ('2023-02-24');

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



INSERT INTO public.question_answer VALUES ('2023-02-20', 'sleep_1_start', '23:59:00');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'sleep_2_end', '08:30:00');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'sleep_hrs', '08:30:00');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'sleep_score', '80');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'steps_cnt', '6826');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'hrs_active', '3');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'mins_activity', '00:47:00');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'sport_trainings', '01:30:00');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'walking', '00:45:00');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'oatmeal_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'meat_eat', '1');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'fish_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'vegetables_eat', '100');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'nuts_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'sugar_eat', '50');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'x_big', '0');
INSERT INTO public.question_answer VALUES ('2023-02-20', 'x_small', '0');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'sleep_1_start', '00:30:00');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'sleep_2_end', '10:30:00');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'sleep_hrs', '09:30:00');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'sleep_score', '73');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'steps_cnt', '5417');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'hrs_active', '6');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'mins_activity', '00:28:00');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'sport_trainings', '00:00:00');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'walking', '00:39:00');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'oatmeal_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'meat_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'fish_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'vegetables_eat', '100');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'nuts_eat', '40');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'sugar_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'x_big', '0');
INSERT INTO public.question_answer VALUES ('2023-02-21', 'x_small', '0');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'sleep_1_start', '00:21:00');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'sleep_2_end', '09:30:00');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'sleep_hrs', '07:30:00');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'sleep_score', '86');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'meat_eat', '1');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'fish_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'x_small', '1');
