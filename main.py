import logging
import random

from data import db_session
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ConversationHandler
from telegram import ReplyKeyboardMarkup
from data.__all_models import User, Questions


BOT_TOKEN = '7970123614:AAF81HYiiFz6EpoptDkMfOiNH9_we1X1-DI'


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR
)

logger = logging.getLogger(__name__)

db_session.global_init('db/site.db')


# noinspection PyUnusedLocal
async def echo(update, context):
    await update.message.reply_text(f'{update.message.text}', reply_markup=markup)


# noinspection PyUnusedLocal
async def start(update, context):
    user_registrarion(update.effective_user)

    user = update.effective_user
    await update.message.reply_html(
        rf'Sup {user.mention_html()}. i`m, like, ur echo, man',
        reply_markup=markup
    )


# noinspection PyUnusedLocal
async def help_command(update, context):
    await update.message.reply_text("Go fuck urself.", reply_markup=markup)


# noinspection PyUnusedLocal
def user_registrarion(tg_user):
    db_sess = db_session.create_session()

    ids = [i.telegram_id for i in db_sess.query(User).all()]

    if tg_user.id not in ids:
        user = User()
        user.name = tg_user.name
        user.telegram_id = tg_user.id
        db_sess = db_session.create_session()
        db_sess.add(user)
        db_sess.commit()
        print('Registered')

    db_sess.close()


# noinspection PyUnusedLocal
async def get_random_questions(update, context):
    db_sess = db_session.create_session()

    if db_sess.query(Questions).all():
        question = random.choice(db_sess.query(Questions).all())

        author_name = db_sess.query(User).filter(User.telegram_id.like(question.author_tg_id)).first().name
        answers = [question.answer_1,
                   question.answer_2,
                   question.answer_3,
                   question.answer_4]
        answer_sheet = []
        for i in range(len(answers)):
            if answers[i] is not None:
                answer_sheet.append(f'{i + 1}: {answers[i]}')
        answer_sheet = '\n'.join(answer_sheet)

        question_repr = [
            f'Author: {author_name}',
            '',
            f'Content: {question.content}',
            '',
            f'Answers: \n{answer_sheet}'
        ]
        question_repr = '\n'.join(question_repr)

        keyboard = [['1', '2']]
        if len(answer_sheet.split('\n')) == 3:
            keyboard.append(['3'])
        elif len(answer_sheet.split('\n')) == 4:
            keyboard.append(['3', '4'])

        if question:
            await update.message.reply_text(question_repr,
                                            reply_markup=ReplyKeyboardMarkup(keyboard,
                                                                             one_time_keyboard=True))
            return 1
    else:
        await update.message.reply_text('Sorry, no questions are available at the moment.')
        return ConversationHandler.END

    db_sess.close()


# noinspection PyUnusedLocal
async def stats(update, context):
    global markup
    await update.message.reply_text(f'Your answer: {update.message.text}', reply_markup=markup)
    return ConversationHandler.END


application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))

conv_handler = ConversationHandler(
        entry_points=[CommandHandler('get_question', get_random_questions)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, stats)],
        },

        fallbacks=[CommandHandler('stop', ...)])

reply_keyboard = [['/start', '/help'],
                  ['/get_question']]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

application.run_polling()
