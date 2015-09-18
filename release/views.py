from django.shortcuts import render,  redirect, HttpResponse
from .models import Release, DeploymentFact, Artifact, Environment
from datetime import date, timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json

PLAN_STATUSES = [Release.NEW, Release.IN_PROGRESS, Release.READY]
HISTORY_STATUSES = [Release.CANCELED, Release.FAILED, Release.SUCCESSFUL]
PLAN = 'plan'
HISTORY = 'history'

MONTH = 'month'
WEEK = 'week'
DAYS = { MONTH: 28, WEEK: 7 }
DEFAULT_MAX_RELEASE_FOR_DAY = 7


def period(request, status, period, year, month, day):
    if period == MONTH:
        number_of_days = DAYS[MONTH]
    else:
        number_of_days = DAYS[WEEK]

    if status == PLAN:
        statuses = PLAN_STATUSES
    else:
        statuses = HISTORY_STATUSES

    start = date(int(year), int(month), int(day))
    end = start + timedelta(number_of_days)
    releases = Release.objects.filter(start_time__range=(start, end)).filter(status__in=statuses).order_by('start_time')

    days = {}
    for delta in range(0, number_of_days):
        d = start + timedelta(delta)
        days[d] = []

    for release in releases:
        days[release.start_time.date()].append(release)
    max_releases_per_day = max(map(lambda x: len(x), days.values()))
    if period == MONTH and max_releases_per_day < DEFAULT_MAX_RELEASE_FOR_DAY:
        max_releases_per_day = DEFAULT_MAX_RELEASE_FOR_DAY

    return render(request, period + '.html', context={
        'day': day,
        'month': month,
        'year': year,
        'releases': days,
        'days': sorted(days.keys()),
        'max_releases_range': range(0, max_releases_per_day),
        'prev_period': start - timedelta(number_of_days),
        'next_period': start + timedelta(number_of_days),
        'status': status,
        'period': period,
        'statuses': [PLAN, HISTORY],
        'periods': [WEEK, MONTH]
    })


def index(request):
    d = date.today()
    return redirect('plan/week/' + str(d.year) + '/' + str(d.month) + '/' + str(d.day))


def fact_list(request):

    if request.method == 'POST':
        body = request.POST
        page = 1
    else:
        body = request.GET
        page = body['page']

    host = body['host']
    artifact = body['artifact']
    version = body['version']

    if body['date']:
        buf_date = (body['date'], (datetime.strptime(body['date'], '%Y-%m-%d') + timedelta(1)))
    else:
        buf_date = 0

    result = create_db_request(host, artifact, version, buf_date)

    if result:
        result2 = ''
    else:
        result2 = 'Nothing Found'

    paginator = Paginator(result, 100)
    try:
        pagin_result = paginator.page(page)
    except PageNotAnInteger:
        pagin_result = paginator.page(1)
    except EmptyPage:
        pagin_result = paginator.page(paginator.num_pages)
    return render(request, 'fact.html', context={
        'result': pagin_result,
        'result2': result2,
        'host': host,
        'artifact': artifact,
        'version': version,
        'date': body['date']
    })


def create_db_request(host, artifact, version, buf_date):
    fact = DeploymentFact.objects

    def check(x):
        if x:
            i = '1'
        else:
            i = '0'
        return i

    iterator = '' + check(host) + check(artifact) + check(version) + check(buf_date)

    result = {}
    result['1000'] = lambda: fact.filter(host=host).order_by('-datetime')
    result['1100'] = lambda: fact.filter(host=host).filter(artifact__type__name=artifact).order_by('-datetime')
    result['1110'] = lambda: fact.filter(host=host).filter(artifact__type__name=artifact).filter(
        artifact__version=version).order_by('-datetime')
    result['1111'] = lambda: fact.filter(host=host).filter(artifact__type__name=artifact).filter(
        artifact__version=version).filter(datetime__range=buf_date).order_by('-datetime')
    result['1101'] = lambda: fact.filter(host=host).filter(artifact__type__name=artifact).filter(
        datetime__range=buf_date).order_by('-datetime')
    result['1010'] = lambda: fact.filter(host=host).filter(artifact__version=version).order_by('-datetime')
    result['1011'] = lambda: fact.filter(host=host).filter(artifact__version=version).filter(
        datetime__range=buf_date).order_by('-datetime')
    result['1001'] = lambda: fact.filter(host=host).filter(datetime__range=buf_date).order_by('-datetime')
    result['0100'] = lambda: fact.filter(artifact__type__name=artifact).order_by('-datetime')
    result['0110'] = lambda: fact.filter(artifact__type__name=artifact).filter(
        artifact__version=version).order_by('-datetime')
    result['0111'] = lambda: fact.filter(artifact__type__name=artifact).filter(
        artifact__version=version).filter(datetime__range=buf_date).order_by('-datetime')
    result['0101'] = lambda: fact.filter(artifact__type__name=artifact).filter(
        datetime__range=buf_date).order_by('-datetime')
    result['0010'] = lambda: fact.filter(artifact__version=version).order_by('-datetime')
    result['0011'] = lambda: fact.filter(artifact__version=version).filter(datetime__range=buf_date).order_by('-datetime')
    result['0001'] = lambda: fact.filter(datetime__range=buf_date).order_by('-datetime')
    result['0000'] = lambda: fact.all().order_by('-datetime')
    return result[iterator]()


@csrf_exempt
def fact_create(request):
    body = json.loads(request.body.decode('utf-8'))
    error_response = ''
    try:
        artifact = Artifact.objects.filter(type__name=body['artifact']).filter(version=body['version'])[0]
        error_response += ''
    except:
        artifact = ''
        error_response += 'artifact not found \n'
    try:
        environment = Environment.objects.get(name=body['environment'])
        error_response += ''
    except:
        environment = ''
        error_response += 'environment not found \n'

    if body['status'] == 'FL' or body['status'] == 'SC':
        print(body['status'])
        status = body['status']
        error_response += ''
    else:
        print(body['status'])
        status = ''
        error_response += 'status incorrect \n'

    if artifact and environment and status:
        fact = DeploymentFact.objects.create(status=status,
                                             host=body['host'],
                                             artifact=artifact,
                                             environment=environment)
        fact.save()
        return HttpResponse(status=200)
    else:
        return HttpResponse(error_response)


def fact_show(request):
    return render(request, 'factshow.html')
