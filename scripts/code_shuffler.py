import datetime
import random
import schedule


last_update = datetime.datetime.now()


def shuffle():
    global last_update

    code = list(open('../db/code.txt').readlines()[0][:-1])
    random.shuffle(code)
    with open('../db/code.txt', 'w') as file:
        file.write(''.join(code) + f'\n{datetime.datetime.now()}')
        print(f'{datetime.datetime.now()}: {len(code)}')


schedule.every(3600).seconds.do(shuffle)
while True:
    schedule.run_pending()
