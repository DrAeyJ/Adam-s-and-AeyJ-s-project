import logging
import random

from data import db_session
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ConversationHandler
from telegram import ReplyKeyboardMarkup
from data.__all_models import User, Questions
from data.env import BOT_TOKEN, reply_keyboard

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR
)
logger = logging.getLogger(__name__)
db_session.global_init('db/site.db')
mode = 'u'
current_question = Questions
current_answers = []


# noinspection PyUnusedLocal
async def echo(update, context):
    await update.message.reply_text(f'{update.message.text}', reply_markup=markup)


# noinspection PyUnusedLocal
async def start(update, context):
    global mode
    global markup

    user_registrarion(update.effective_user)
    user = update.effective_user
    db_sess = db_session.create_session()

    if db_sess.query(User).filter(User.telegram_id.like(user.id)).first().type == 'Unregistered':
        mode = 'u'
        application.add_handler(CommandHandler("register", register))
    elif db_sess.query(User).filter(User.telegram_id.like(user.id)).first().type == 'Registered':
        application.add_handler(conv_handler)
        mode = 'r'
    elif db_sess.query(User).filter(User.telegram_id.like(user.id)).first().type == 'Moderator':
        application.add_handler(conv_handler)
        mode = 'm'
    markup = ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False)

    await update.message.reply_html(f'Hi {user.mention_html()}. I am a questionaire.', reply_markup=markup)


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
    global current_question
    global current_answers

    db_sess = db_session.create_session()

    if db_sess.query(Questions).all():
        question = random.choice(db_sess.query(Questions).all())
        current_question = question
        author_name = db_sess.query(User).filter(User.telegram_id.like(question.author_tg_id)).first().name
        answers = [question.answer_1,
                   question.answer_2,
                   question.answer_3,
                   question.answer_4]
        answer_sheet = []
        emote = '1️⃣'[1:]
        for i in range(len(answers)):
            if answers[i] is not None:
                answer_sheet.append(f'{str(i + 1) + emote}: {answers[i]}')
        current_answers = answer_sheet
        answer_sheet = '\n'.join(answer_sheet)

        question_repr = [
            f'Author: {author_name}                             ',
            '',
            f'Content: {question.content}',
            '',
            f'Answers: \n{answer_sheet}'
        ]
        question_repr = '\n'.join(question_repr)

        keyboard = [['1️⃣', '2️⃣']]
        if len(answer_sheet.split('\n')) == 3:
            keyboard.append(['3️⃣'])
        elif len(answer_sheet.split('\n')) == 4:
            keyboard.append(['3️⃣', '4️⃣'])
        keyboard.append(['/stop'])

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
    global current_question
    global current_answers

    if int(update.message.text[0]) in list(range(1, len(current_answers) + 1)):
        answers = [current_question.answer_1_count,
                   current_question.answer_2_count,
                   current_question.answer_3_count,
                   current_question.answer_4_count]
        ans = []
        for i in range(len(answers)):
            if answers[i] is not None:
                ans.append(answers[i])
        ans1 = []
        emote = '1️⃣'[1:]
        for i in range(len(ans)):
            try:
                ans1.append(f'{str(i + 1) + emote}: {round(ans[i] / sum(ans) * 100)}%')
            except ZeroDivisionError:
                ans1.append(f'{str(i + 1) + emote}: 0%')
        ans1 = '\n'.join(ans1)
        answer_repr = [
            f'Your answer: {update.message.text}                             ',
            '',
            f'Answer precentage: \n{ans1}',
            '',
            f'Likes: {current_question.likes_count}',
            f'Dislikes: {current_question.dislikes_count}',
            f'Reports: {current_question.reports_count}'
        ]
        answer_repr = '\n'.join(answer_repr)

        match update.message.text[0]:
            case '1':
                db_sess = db_session.create_session()
                db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().answer_1_count += 1
                db_sess.commit()
                db_sess.close()
            case '2':
                db_sess = db_session.create_session()
                db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().answer_2_count += 1
                db_sess.commit()
                db_sess.close()
            case '3':
                db_sess = db_session.create_session()
                db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().answer_3_count += 1
                db_sess.commit()
                db_sess.close()
            case '4':
                db_sess = db_session.create_session()
                db_sess.query(Questions).filter(Questions.id.like(current_question.id)).first().answer_4_count += 1
                db_sess.commit()
                db_sess.close()

        await update.message.reply_text(answer_repr, reply_markup=markup)
        return ConversationHandler.END
    else:
        keyboard = [['1️⃣', '2️⃣']]
        if len(current_answers) == 3:
            keyboard.append(['3️⃣'])
        elif len(current_answers) == 4:
            keyboard.append(['3️⃣', '4️⃣'])

        await update.message.reply_text('Invalid answer. Please, type in a valid answer.',
                                        reply_markup=ReplyKeyboardMarkup(keyboard,
                                                                         one_time_keyboard=True))
        return 1


# noinspection PyUnusedLocal
async def stop(update, context):
    await update.message.reply_text('Questionaire ended.', reply_markup=markup)
    return ConversationHandler.END


# noinspection PyUnusedLocal
async def register(update, context):
    global mode
    global markup

    mode = 'r'
    markup = ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False)
    db_sess = db_session.create_session()
    db_sess.query(User).filter(User.telegram_id.like(update.effective_user.id)).first().type = 'Registered'
    db_sess.commit()
    db_sess.close()
    application.add_handler(conv_handler)

    await update.message.reply_text('User type changed to: Registered.', reply_markup=markup)


application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
conv_handler = ConversationHandler(
        entry_points=[CommandHandler('get_question', get_random_questions)],

        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, stats)],
        },

        fallbacks=[CommandHandler('stop', stop)])

markup = ReplyKeyboardMarkup(reply_keyboard[mode], one_time_keyboard=False)

application.run_polling()
