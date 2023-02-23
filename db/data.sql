


INSERT INTO public.day VALUES ('2023-02-20', true);
INSERT INTO public.day VALUES ('2023-02-21', true);
INSERT INTO public.day VALUES ('2023-02-22', true);
INSERT INTO public.day VALUES ('2023-02-23', true);
INSERT INTO public.day VALUES ('2023-02-24', true);


--
-- Data for Name: question_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.question_type VALUES (0, 'plain', '');
INSERT INTO public.question_type VALUES (1, 'int', '(D)');
INSERT INTO public.question_type VALUES (2, 'binary', '(0/1)');
INSERT INTO public.question_type VALUES (3, 'time', '(H)');

--
-- Data for Name: question; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.question VALUES ('sleep_1_start', 2, '`(H)` Отбой (время)', '{22:00,23:00,00:00,01:00}', 3, true);
INSERT INTO public.question VALUES ('sleep_2_end', 3, '`(H)` Подъем (время)', '{08:00,09:00,10:00,11:00,12:00}', 3, true);
INSERT INTO public.question VALUES ('sleep_score', 5, '`(0-100)` Sleep score (h-w-gt3)', '{50,75,100}', 1, true);
INSERT INTO public.question VALUES ('steps_cnt', 6, '`(D)` Steps count  (h-w-gt3)', '{6000,8000,10000,20000}', 1, true);
INSERT INTO public.question VALUES ('mins_activity', 8, '`(H)` Minutes activity (h-w-gt3)', '{00:00,00:30,01:00,01:30}', 3, true);
INSERT INTO public.question VALUES ('sport_trainings', 9, '`(H)` Спорт. тренировки (часы)?', '{00:00,00:30,01:00,01:30}', 3, true);
INSERT INTO public.question VALUES ('walking', 10, '(H) Прогулка (часы)?', '{00:00,00:30,01:00,01:30}', 3, true);
INSERT INTO public.question VALUES ('oatmeal_eat', 11, '`(0/1)` Овсянка?', '{Да,Нет}', 2, true);
INSERT INTO public.question VALUES ('meat_eat', 12, '`(0/1)` Мясо?', '{Да,Нет}', 2, true);
INSERT INTO public.question VALUES ('fish_eat', 13, '`(0/1)` Рыба?', '{Да,Нет}', 2, true);
INSERT INTO public.question VALUES ('vegetables_eat', 14, '`(Grams)` Овощи?', '{0,50,100,150}', 1, true);
INSERT INTO public.question VALUES ('nuts_eat', 15, '`(Grams)` Орехи?', '{0,40,80,120}', 1, true);
INSERT INTO public.question VALUES ('sugar_eat', 16, '`(0-10)` Сладкое?', '{0,1,2,3,4,5,6,7,8,9,10}', 1, true);
INSERT INTO public.question VALUES ('x_big', 17, 'X?', '{1,0}', 2, true);
INSERT INTO public.question VALUES ('x_small', 18, '(x)?', '{1,0}', 2, true);
INSERT INTO public.question VALUES ('sleep_hrs', 1, '`(H)` Sleep hours (hours) (h-w-gt3)', '{7.5,8,8.5,9}', 3, true);
INSERT INTO public.question VALUES ('hrs_active', 10, '`(D)` Hours active  (h-w-gt3)', '{0,1,2,6,8,12}', 1, true);
INSERT INTO public.question VALUES ('breakfast_end', 5, 'breakfast_end', '{09:00,10:00,11:00,12:00}', 3, false);
INSERT INTO public.question VALUES ('vitamin_d3_supply', 6, 'vitamin_d3_supply', '{0,5000,6000}', 1, false);
INSERT INTO public.question VALUES ('omega_3_supply', 6, 'omega_3_supply', '{0,1.5}', 1, false);
INSERT INTO public.question VALUES ('weight', 0, 'Weight', '{65,66,67,70}', 1, false);


--
-- Data for Name: question_answer; Type: TABLE DATA; Schema: public; Owner: postgres
--

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
INSERT INTO public.question_answer VALUES ('2023-02-22', 'steps_cnt', '2128');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'hrs_active', '4');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'mins_activity', '00:06:00');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'sport_trainings', '00:00:00');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'walking', '00:00:00');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'oatmeal_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'meat_eat', '1');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'fish_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'vegetables_eat', '100');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'nuts_eat', '40');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'sugar_eat', '0.0');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'x_big', '0');
INSERT INTO public.question_answer VALUES ('2023-02-22', 'x_small', '1');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'sleep_1_start', '01:10:00');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'sleep_2_end', '09:40:00');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'sleep_hrs', '08:19:00');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'sleep_score', '94');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'steps_cnt', NULL);
INSERT INTO public.question_answer VALUES ('2023-02-23', 'hrs_active', NULL);
INSERT INTO public.question_answer VALUES ('2023-02-23', 'mins_activity', '00:49:00');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'sport_trainings', '00:00:00');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'walking', '01:00:00');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'oatmeal_eat', '0');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'meat_eat', '1.0');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'fish_eat', '0.0');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'vegetables_eat', '150');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'nuts_eat', '25');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'sugar_eat', '0.0');
INSERT INTO public.question_answer VALUES ('2023-02-23', 'x_big', NULL);
INSERT INTO public.question_answer VALUES ('2023-02-23', 'x_small', '1');
