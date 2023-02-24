# @dataclass
# class Question:
#     name: str
#
#     text: str
#     inline_keyboard_answers: list[str]
#     answer_apply_func: Optional[Callable] = None
#
#     def __str__(self):
#         # return f'[{self.number}] {self.text}'
#         return '{:15} {}'.format(self.name, self.text)
import dataclasses

# from db import _query_get, _psql_conn, _query_set


class Table:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self.__init__(*args, **kwargs)


class ObjectsManager:
    db_class = None
    table_name: str

    def __init__(self, db_class, table_name: str):
        self.db_class = db_class
        self.table_name = table_name

    def get_all(self, ) -> list[Table]:
        query = """
            -- Print all questions list
            SELECT * FROM {};
        """.format(self.table_name)
        # ORDER BY q.num_int;
        obj_list: list = []

        query_results = _query_get(
            _psql_conn(),
            query,
            # (self.table_name,)
        )

        for row in query_results:
            obj = self.db_class(*row)
            obj_list.append(obj)

        return obj_list

    def create(self, **kwargs):
        keys = tuple(kwargs.keys())
        values = tuple(kwargs.values())

        cols_list_str = str(keys).replace("'", "")

        parameters_str = "(" + "%s, " * (len(values) - 1) + "%s)"

        query = 'INSERT INTO {} {} VALUES {};'.format(
            self.table_name,
            cols_list_str,
            parameters_str
        )

        _query_set(
            _psql_conn(),
            query,
            (*values,)
        )

        obj = self.db_class(**kwargs)
        return obj

    # def exists(self/):



if __name__ == "__main__":
    # QuestionDB.get_questions()

    # om = ObjectsManager(QuestionDB, 'question')
    #
    # print(om.get_all())

    # om2 = ObjectsManager(QuestionTypeDB, 'question_type')
    # pprint(om2.get_all())

    # qt = om2.create(id=44, name='name44', notation_str='notat44')
    # print(qt)
    pass