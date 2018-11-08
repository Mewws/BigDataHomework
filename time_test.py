import datetime


# begin_time = datetime.datetime.strptime('2018-01-01', '%Y-%m-%d')

begin_time = datetime.date(2017, 1, 2)
end_time = begin_time + datetime.timedelta(days=6)

while(end_time < datetime.date.today()):

    print(begin_time)
    print(end_time)
    begin_time = begin_time + datetime.timedelta(days=7)
    end_time = begin_time + datetime.timedelta(days=6)


