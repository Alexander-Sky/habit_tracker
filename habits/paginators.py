from rest_framework.pagination import LimitOffsetPagination


class HabitPaginator(LimitOffsetPagination):
    """Пагинация привычек: по пять на страницу.

    Клиент может попросить другой размер параметром limit, но не больше
    max_limit — иначе одним запросом можно было бы вытащить всю базу.

    Ответ: {count, next, previous, results}.
    """

    default_limit = 5
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100
