from datetime import date

from django.db.models import Max, Min


def worklog_period(obj):
    activity_period = obj.worklogentries.aggregate(Max('date'), Min('date'))
    article_period = obj.articleentries.aggregate(Max('date'), Min('date'))

    min_date = date(1900, 1, 1)
    max_date = date(3000, 1, 1)

    if not (activity_period['date__min'] or article_period['date__min']):
        return (min_date, max_date)

    start = min(activity_period['date__min'] or max_date, article_period['date__min'] or max_date)
    end = max(activity_period['date__max'] or min_date, article_period['date__max'] or min_date)

    return (start, end)


def worklog_period_string(obj):
    start, end = worklog_period(obj)

    return u'%s - %s' % (start.strftime('%d.%m.%Y'), end.strftime('%d.%m.%Y'))
