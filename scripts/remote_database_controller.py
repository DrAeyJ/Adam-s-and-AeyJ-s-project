import flask
import db_session
import __all_models

app = flask.Flask(__name__)
db_session.global_init('../db/site.db')


@app.route('/change_user_type/<user_type>/<int:telegram_id>/<admin_passcode>')
def cut(user_type, telegram_id, admin_passcode):
    if check(admin_passcode) and user_type in ['Unregistered', 'Registered', 'Moderator', 'Premium', 'Admin']:
        db_sess = db_session.create_session()
        db_sess.query(__all_models.User).filter(
            __all_models.User.telegram_id.like(telegram_id)).first().type = user_type
        db_sess.commit()
        name = db_sess.query(__all_models.User).filter(__all_models.User.telegram_id.like(telegram_id)).first().name
        db_sess.close()
        return {'Request granted': 'Y',
                'msg': f'User by the name of {name}({telegram_id}) has been granted {user_type} role.'}
    else:
        response = {'Request granted': 'N'}
        if user_type not in ['Unregistered', 'Registered', 'Moderator', 'Premium', 'Admin']:
            response['msg'] = 'Wrong User type.'
        elif not check(admin_passcode):
            response['msg'] = 'Wrong passcode.'
        return response


def check(code_given):
    code = open('../db/code.txt').readlines()[0][:-1]
    if code_given == code:
        return True
    else:
        return False


app.run()
