from flask import Flask, request, redirect, render_template, session, send_file
from collections import OrderedDict
import app.settings as settings
from datetime import datetime
from app.models import *
import requests
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = settings.max_content_length
app.config['TEMPLATES_AUTO_RELOAD'] = settings.templates_auto_reload
app.secret_key = settings.secret_key
app.static_folder = settings.static_folder
app.template_folder = settings.template_folder
app.jinja_env.globals.update(options=options)
app.jinja_env.globals.update(debug=settings.debug)


def check_captcha(g_recaptcha_response):
    data = {
        'response': g_recaptcha_response,
        'secret': options['recaptcha_secret_key']
    }
    response = requests.post(
        'https://www.google.com/recaptcha/api/siteverify', data=data).json()
    print(response)
    return response['success'] and response['action'] == 'submit' and response['score'] >= 0.5


@app.before_request
def check_session():
    if request.path.startswith('/admin/') and request.path != '/admin/login' and 'admin_id' not in session.keys():
        return redirect('/admin/login')


@app.route('/')
def home_page():
    return render_template('pages/home.html')


@app.route('/publish')
def publish_page():
    return render_template('pages/publish.html')


@app.route('/publish', methods=['POST'])
def publish_process():
    if not debug and not check_captcha(request.form.get('g-recaptcha-response')):
        raise Exception('Wrong captcha answer!')

    file = request.files['file']
    if file.content_type != 'application/pdf':
        raise Exception('Given file is not the PDF!')
    order = BookOrder.create(format='ebook', status='shipping', created=datetime.now(
    ), price=options['ebook_price'], publication_date=datetime.strptime(request.form.get('publication_date'), '%m/%d/%Y'))
    file.save(os.path.join(settings.books_folder, f'{order.id}.pdf'))
    session['order_id'] = order.id
    return redirect('/shipping')


@app.route('/shipping')
def shipping_page():
    if 'order_id' not in session.keys():
        return redirect('/publish')

    order = BookOrder.get(session['order_id'])
    if order.status != 'shipping':
        return redirect('/publish')

    return render_template('pages/shipping.html', order=order)


@app.route('/shipping', methods=['POST'])
def shipping_process():
    customer_details = OrderedDict()
    customer_details['First Name'] = request.form.get('first_name')
    customer_details['Last Name'] = request.form.get('last_name')
    customer_details['Email Address'] = request.form.get('email')
    payment_details = {'payment_method': 'paypal'}
    BookOrder.update(status='payment', customer_details=list(customer_details.items(
    )), payment_details=payment_details).where(BookOrder.id == session['order_id']).execute()
    return redirect('/payment')


@app.route('/payment')
def payment_page():
    if 'order_id' not in session.keys():
        return redirect('/publish')

    order = BookOrder.get(session['order_id'])
    if order.status == 'shipping':
        return redirect('/shipping')
    elif order.status != 'payment':
        return redirect('/publish')

    return render_template('pages/payment.html', order=order)


@app.route('/submit/paypal')
def paypal_submit_page():
    order_id = request.args.get('order_id')
    order = BookOrder.get(BookOrder.id == order_id)
    paypal_order_id = request.args.get('paypal_order_id')

    response = requests.post('https://api-m.sandbox.paypal.com/v1/oauth2/token', data={
                             'grant_type': 'client_credentials'}, auth=(options['paypal_client_id'], options['paypal_client_secret']))

    response = requests.get(f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{paypal_order_id}', headers={
        'Authorization': f'Bearer {response.json()["access_token"]}',
    }).json()

    if response['intent'] == 'CAPTURE' and response['status'] in ['APPROVED', 'COMPLETED'] and response['purchase_units'][0]['invoice_id'] == order_id and response['purchase_units'][0]['amount']['currency_code'] == 'USD' and float(response['purchase_units'][0]['amount']['value']) == order.price:
        BookOrder.update(status='paid').where(
            BookOrder.id == order_id).execute()
        if 'order_id' in session.keys() and session['order_id'] == int(order_id):
            del session['order_id']
        return render_template('pages/error.html', error_code=f'Order #{order_id}', error_title='successfully paid', error_description='Thanks for the payment!\nWe have accepted your order for processing. We will contact you soon.')

    payment_id = response['purchase_units'][0]['payments']['captures'][0]['id']
    return render_template('pages/error.html', error_code=f'Order #{order_id}', error_title='error while checking your payment', error_description=f'There seems to be something wrong with your payment.<br>If you are sure that the payment has been completed, write to us, informing us of the order number (<code>{order_id}</code>) and PayPal Payment ID (<code>{payment_id}</code>).')


@app.route('/about')
def about_page():
    return render_template('pages/about.html')


@app.route('/help')
def help_page():
    return render_template('pages/help.html')


@app.route('/admin/login')
def admin_login_page():
    if 'admin_id' in session.keys():
        return redirect('/admin/orders')

    return render_template('pages/admin/login.html')


@app.route('/admin/login', methods=['POST'])
def admin_login_process():
    if not debug and not check_captcha(request.form.get('g-recaptcha-response')):
        return render_template('pages/admin/login.html', error=True)

    email = request.form.get('email')
    password = request.form.get('password')
    if Admin.select().where(Admin.email == email, Admin.password == password).count():
        session['admin_id'] = Admin.get(
            Admin.email == email, Admin.password == password).id
        return redirect('/admin/orders')
    return render_template('pages/admin/login.html', error=True)


@app.route('/admin/logout')
def admin_logout_page():
    if 'admin_id' in session.keys():
        del session['admin_id']
    return redirect('/')


@app.route('/admin/orders')
def admin_orders_page():
    page = int(request.args.get('page') or 1)
    orders = BookOrder.select().order_by(
        BookOrder.id.desc()).offset((page - 1) * 20).limit(20)
    pages_before = page > 1
    pages_after = BookOrder.select().count() > page * 20
    return render_template('pages/admin/orders.html', orders=orders, pages_before=pages_before, pages_after=pages_after, page=page)


@app.route('/admin/orders/<int:order_id>')
def admin_order_page(order_id):
    return render_template('pages/admin/order.html', order=BookOrder.get(order_id))


@app.route('/admin/orders/<int:order_id>/done')
def admin_done_order_page(order_id):
    BookOrder.update(status='done').where(BookOrder.id == order_id).execute()
    return redirect(f'/admin/orders/{order_id}')


@app.route('/admin/orders/<int:order_id>.pdf')
def admin_order_download_page(order_id):
    order = BookOrder.get(order_id)
    return send_file(os.path.join(settings.books_folder, f'{order.id}.pdf'))


@app.route('/admin/options')
def admin_options_page():
    option_names = ['company_name', 'company_copyright', 'company_address',
                    'recaptcha_site_key', 'recaptcha_secret_key', 'ebook_price',
                    'paypal_client_id', 'paypal_client_secret']
    options = Option.select().where(Option.name.in_(option_names))
    return render_template('pages/admin/options.html', editable_options=options)


@app.route('/admin/options', methods=['POST'])
def admin_options_process():
    for name in request.form.keys():
        Option.update(value=request.form.get(name)).where(
            Option.name == name).execute()
    return redirect('/admin/options')


@app.route('/admin/texts')
def admin_texts_page():
    text_names = ['home_block', 'publish_block', 'about_block', 'help_block']
    texts = Option.select().where(Option.name.in_(text_names))
    return render_template('pages/admin/texts.html', texts=texts)


@app.route('/admin/texts', methods=['POST'])
def admin_texts_process():
    for name in request.form.keys():
        Option.update(value=request.form.get(name)).where(
            Option.name == name).execute()
    return redirect('/admin/texts')


@app.errorhandler(404)
def error_404(error):
    return render_template('pages/error.html', error_code=404, error_title='Not Found', error_description='Sorry, the page was not found. Check the page address or go back to the main page.', is_admin=request.path.startswith('/admin/')), 404


@app.errorhandler(500)
def error_500(error):
    return render_template('pages/error.html', error_code=500, error_title='Server Error', error_description='Sorry, there was a server error. Please check the sent data or use the service later.', is_admin=request.path.startswith('/admin/')), 500
