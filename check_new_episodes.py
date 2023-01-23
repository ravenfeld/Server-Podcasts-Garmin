from apscheduler.schedulers.blocking import BlockingScheduler
import manager_podcast

sched = BlockingScheduler()


@sched.scheduled_job('cron', day_of_week='mon-sun', hour=4)
def scheduled_job():
    print('Cron checkNewEpisodes')
    manager_podcast.create_database()
    manager_podcast.check_new_episodes(0)


sched.start()
