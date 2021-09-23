import django_filters as filters


class BaseFilters(filters.FilterSet):

    order_by = filters.CharFilter(method='order_by_filter')

    def order_by_filter(self, qs, name, value):
        return qs.order_by(value)
