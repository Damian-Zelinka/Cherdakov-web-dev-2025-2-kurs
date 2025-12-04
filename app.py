import csv
import io
from flask import Flask, abort, make_response, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from models import *
# from flask_migrate import Migrate
import os
from werkzeug.utils import secure_filename
import time
from decimal import Decimal
from sqlalchemy.sql.expression import func
from functools import wraps


app = Flask(__name__)
app.config.from_pyfile('config.py')

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@bee_db:5432/lab2"  # fallback for local Docker
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
# migrate = Migrate(app, db)




# Инициализация БД
with app.app_context():
    db.create_all()

with app.app_context():
    if Role.query.count() == 0:
        db.session.add_all([
            Role(name='Администратор'),
            Role(name='Пользователь')
        ])
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_cart_data():
    cart = session.get('cart', {})
    total_items = sum(cart.values())
    return {
        'cart_items_count': total_items,
        'bee_coins': current_user.bee_coins if current_user.is_authenticated else 0
    }



@app.route('/')
def index():
    random_products = Product.query.order_by(func.random()).limit(3).all()
    return render_template('index.html', random_products=random_products)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        user = User.query.filter_by(login=login).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/demo')
@login_required
def pr_demo():
    return render_template('demo.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

def validate_user_data(data, is_edit=False):
    errors = {}
    
    if not is_edit:
        # Валидация логина
        login = data.get('login', '').strip()
        if not login:
            errors['login'] = 'Логин обязателен'
        elif len(login) < 5:
            errors['login'] = 'Логин должен быть не короче 5 символов'
        elif not login.isalnum():
            errors['login'] = 'Логин должен содержать только буквы и цифры'
        elif User.query.filter_by(login=login).first():
            errors['login'] = 'Этот логин уже занят'

    if not is_edit:
        # Валидация пароля через общую функцию
        password = data.get('password', '')
        password_errors = validate_password(password)
        if password_errors:
            errors['password'] = ", ".join(password_errors)

    # Валидация имени
    first_name = data.get('first_name', '').strip()
    if not first_name:
        errors['first_name'] = 'Имя обязательно'

    return errors

def validate_password(password):
    errors = []
    special_chars = {'~','!','?','@','#','$','%','^','&','*','_','-','+',
                    '(',')','[',']','{','}','>','<','/','\\','|','"',"'",'.',',',':',';'}
    
    if len(password) < 8:
        errors.append("Минимум 8 символов")
    if len(password) > 128:
        errors.append("Максимум 128 символов")
    if not any(c.isupper() for c in password):
        errors.append("Хотя бы одна заглавная буква")
    if not any(c.islower() for c in password):
        errors.append("Хотя бы одна строчная буква")
    if not any(c.isdigit() for c in password):
        errors.append("Хотя бы одна цифра")
    if ' ' in password:
        errors.append("Без пробелов")
    if not all(c.isalnum() or c in special_chars for c in password):
        errors.append("Недопустимые символы")
    
    return errors

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        errors = {}
        
        # Проверка старого пароля
        if not current_user.check_password(old_password):
            errors['old_password'] = 'Неверный текущий пароль'
        
        # Валидация нового пароля
        password_errors = validate_password(new_password)
        if password_errors:
            errors['new_password'] = ", ".join(password_errors)
        
        # Проверка совпадения паролей
        if new_password != confirm_password:
            errors['confirm_password'] = 'Пароли не совпадают'
        
        if errors:
            for field, message in errors.items():
                flash(message, 'danger')
            return render_template('change_password.html', 
                                 form_data=request.form,
                                 errors=errors)
        
        try:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Пароль успешно изменен', 'success')
            return redirect(url_for('index'))
        
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при изменении пароля', 'danger')
    
    return render_template('change_password.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        

        # Валидация данных
        errors = {}
        if not login:
            errors['login'] = 'Логин обязателен'
        elif User.query.filter_by(login=login).first():
            errors['login'] = 'Логин уже занят'
        
        if not password:
            errors['password'] = 'Пароль обязателен'
        elif password != confirm_password:
            errors['confirm_password'] = 'Пароли не совпадают'
        if not full_name:
            errors['full_name'] = 'Полное имя обязательно'

        if not email:
            errors['email'] = 'Email обязателен'
        elif User.query.filter_by(email=email).first():
            errors['email'] = 'Email уже используется'
                
        
        # Валидация пароля через общую функцию
        password_errors = validate_password(password)
        if password_errors:
            errors['password'] = ", ".join(password_errors)

        if errors:
            for field, message in errors.items():
                flash(message, 'danger')
            return render_template('register.html', 
                                 form_data=request.form)
        try:
            # Создание пользователя
            new_user = User(
                login=login,
                full_name=full_name,
                email=email,
            )
            new_user.set_password(password)
            
            # Назначение роли "Пользователь" по умолчанию
            default_role = Role.query.filter_by(name='Пользователь').first()
            if default_role:
                new_user.role_id = default_role.id
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Регистрация прошла успешно! Теперь можно войти', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при регистрации', 'danger')
    
    return render_template('register.html')



@app.route('/catalog')
def catalog():
    selected_category = request.args.get('category')
    search = request.args.get('search', '').strip()
    price_min = request.args.get('price_min', type=float)
    price_max = request.args.get('price_max', type=float)


    # фильтрация по категории
    query = Product.query
    if selected_category and selected_category != 'All':
        query = query.filter_by(category=selected_category)

    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

   # Фильтрация по цене
    if price_min is not None:
        query = query.filter(Product.price >= price_min)
    if price_max is not None:
        query = query.filter(Product.price <= price_max)

    products = query.order_by(Product.created_at.desc()).all()


    recent_products = products[:2]
    other_products = products[2:]

    return render_template(
        'catalog.html',
        recent_products=recent_products,
        products=other_products,
        selected_category=selected_category or 'All'
    )


@app.route('/bee_coin')
def bee_coin():
    transactions = BeeCoinTransaction.query.filter_by(user_id=current_user.id).order_by(BeeCoinTransaction.created_at.desc()).all()
    return render_template('bee_coin.html', transactions=transactions)

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' in request.files:
        file = request.files['avatar']
        if file.filename != '':
            # Проверяем расширение файла
            if not allowed_file(file.filename):
                flash('Invalid file type. Only images are allowed.', 'danger')
                return redirect(url_for('profile'))
            
            # Создаем папку для аватарок, если ее нет
            upload_folder = os.path.join(app.root_path, 'static', 'avatars')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # Генерируем уникальное имя файла
            ext = file.filename.split('.')[-1]
            filename = secure_filename(f"avatar_{current_user.id}_{int(time.time())}.{ext}")
            filepath = os.path.join(upload_folder, filename)
            
            # Сохраняем файл
            file.save(filepath)
            
            # Удаляем старый аватар, если он есть
            if current_user.avatar:
                old_avatar = os.path.join(upload_folder, current_user.avatar)
                if os.path.exists(old_avatar):
                    os.remove(old_avatar)
            
            # Обновляем запись пользователя
            current_user.avatar = filename
            db.session.commit()
            flash('Avatar updated successfully!', 'success')
        else:
            flash('No file selected', 'danger')
    else:
        flash('No file part', 'danger')
    
    return redirect(url_for('profile'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('profile.html', orders=orders)



@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        form = request.form
        errors = {}

        email = form.get('email', '').strip()
        full_name = form.get('full_name', '').strip()
        phone = form.get('phone', '').strip()
        address = form.get('address', '').strip()

        if not email:
            errors['email'] = 'Email обязателен'
        elif User.query.filter(User.email == email, User.id != current_user.id).first():
            errors['email'] = 'Этот email уже используется другим пользователем'

        if not full_name:
            errors['full_name'] = 'Полное имя обязательно'

        if errors:
            for field, msg in errors.items():
                flash(msg, 'danger')
            return render_template('edit_profile.html', form_data=form, errors=errors)

        # Обновление данных
        current_user.email = email
        current_user.full_name = full_name
        current_user.phone = phone
        current_user.address = address

        try:
            db.session.commit()
            flash('Профиль успешно обновлен', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при сохранении данных: {e}', 'danger')

    return render_template('edit_profile.html', form_data=current_user)


@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)

    cart = session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart

    flash(f"{product.name} added to your cart!", "success")
    return redirect(url_for('catalog'))

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart_redirect(product_id):
    if not current_user.is_authenticated:
        flash("Please log in to add products to cart.", "warning")
        return redirect(url_for('login', next=url_for('add_to_cart', product_id=product_id)))
    return redirect(url_for('add_to_cart', product_id=product_id))


@app.route('/cart', methods=['GET', 'POST'])
@login_required
def cart():
    cart = session.get('cart', {})
    products = []
    total = Decimal('0.00')
    earn_beecoins = 0

    for product_id, qty in cart.items():
        product = Product.query.get(product_id)
        if product:
            total += product.price * qty
            item_beecoins = product.bee_coin * qty
            earn_beecoins += item_beecoins
            products.append({'product': product, 'qty': qty})

    used_beecoins = Decimal('0.00')
    bee_coin_discount = Decimal('0.00')

    if request.method == 'POST':
        try:
            requested = Decimal(request.form.get('beecoin_to_use', '0'))
            max_allowed = min(current_user.bee_coins, total)
            used_beecoins = max(Decimal('0.00'), min(requested, max_allowed))
            bee_coin_discount = used_beecoins
        except:
            flash("Invalid BeeCoin input", "warning")

    return render_template(
        'cart.html',
        products=products,
        total=total - bee_coin_discount,
        beecoins=int(current_user.bee_coins),
        used_beecoins=used_beecoins,
        bee_coin_discount=bee_coin_discount, earn_beecoins=earn_beecoins
    )



@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    cart.pop(str(product_id), None)
    session['cart'] = cart
    return redirect(url_for('cart'))


@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    from decimal import Decimal, ROUND_HALF_UP
    cart = session.get('cart', {})
    if not cart:
        flash("Cart is empty.")
        return redirect(url_for('cart'))

    # Получение всех товаров
    product_ids = [int(pid) for pid in cart.keys()]
    products = Product.query.filter(Product.id.in_(product_ids)).all()

    # Подготовка
    total = Decimal('0.00')
    bee_coin_earned = Decimal('0.00')

    for product in products:
        qty = int(cart[str(product.id)])
        item_total = product.price * qty
        total += item_total

        # Расчёт кешбэка для каждого товара
        cashback = product.bee_coin
        bee_coin_earned += cashback

    # Списание BeeCoin (если указано)
    try:
        used_beecoins = Decimal(request.form.get('beecoin_to_use', '0'))
    except:
        used_beecoins = Decimal('0.00')

    used_beecoins = min(used_beecoins, current_user.bee_coins, total)
    total_after_discount = total - used_beecoins

    # Создание заказа
    order = Order(user_id=current_user.id, total_amount=total_after_discount)
    db.session.add(order)
    db.session.flush()

    for product in products:
        qty = int(cart[str(product.id)])
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=qty,
            price=product.price
        ))

    # Списание BeeCoin, если использовались
    if used_beecoins > 0:
        current_user.bee_coins -= used_beecoins
        db.session.add(BeeCoinTransaction(
            user_id=current_user.id,
            amount=-used_beecoins,
            transaction_type='redeem',
            description=f"Spent on order #{order.id}"
        ))

    # Начисление BeeCoin
    if bee_coin_earned > 0:
        current_user.bee_coins += bee_coin_earned
        db.session.add(BeeCoinTransaction(
            user_id=current_user.id,
            amount=bee_coin_earned,
            transaction_type='earn',
            description=f"Earned from order #{order.id}"
        ))

    db.session.commit()
    session.pop('cart', None)

    flash(f"Order placed successfully. You earned {bee_coin_earned} BeeCoin!", "success")
    return redirect(url_for('index'))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Пожалуйста, войдите в систему.", "warning")
            return redirect(url_for('login'))
        if current_user.role_id != 1:
            flash("Доступ запрещён: только для админов.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function



@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():

    # Пример получения статистики
    product_count = Product.query.count()
    user_count = User.query.count()  # Можно добавить фильтр по активности
    admin_count = User.query.filter_by(role_id=1).count()


    return render_template('admin/dashboard.html',
                       user_count=user_count,
                       product_count=product_count,
                       admin_count=admin_count)


@app.route('/admin/products')
@login_required
@admin_required
def admin_products():

    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products)


@app.route('/admin/products/export')
@login_required
@admin_required
def export_products_csv():


    products = Product.query.all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Category', 'Price', 'BeeCoin', 'Stock'])

    for product in products:
        cw.writerow([product.id, product.name, product.category, float(product.price), float(product.bee_coin), product.stock])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=products.csv"
    output.headers["Content-type"] = "text/csv"
    return output

def save_image(image):
    if image and image.filename:
        # Получаем безопасное имя файла
        filename = secure_filename(image.filename)

        # Добавляем временную метку, чтобы избежать конфликтов имён
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"

        # Папка для загрузок (например: static/uploads)
        upload_folder = os.path.join('static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)  # Создаём, если нет

        # Полный путь для сохранения
        file_path = os.path.join(upload_folder, filename)
        image.save(file_path)

        # Возвращаем путь для использования в шаблоне
        return f"/static/images/{filename}"
    return None


@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        bee_coin = int(request.form['bee_coin'])
        image = request.files.get('image')
        
        image_url = save_image(image) if image else None 
        
        new_product = Product(name=name, category=category, price=price, bee_coin=bee_coin, image_url=image_url)
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('admin_products'))

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):


    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.category = request.form['category']
        product.price = float(request.form['price'])
        product.bee_coin = float(request.form['bee_coin'])

        if 'image' in request.files and request.files['image'].filename != '':
            product.image_url = save_image(request.files['image'])

        db.session.commit()
        return redirect(url_for('admin_products'))

    return render_template('admin/products.html', products=Product.query.all(), edit_product=product)


@app.route('/admin/products/delete/<int:product_id>')
@login_required
@admin_required
def delete_product(product_id):

    # Удаление продукта
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully', 'success')
    return redirect(url_for('admin_products'))

@app.route('/export_users')
@admin_required
@login_required
def export_users():
    users = User.query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Имя', 'Email'])

    for user in users:
        writer.writerow([user.id, user.full_name, user.email])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=users.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# Страница со списком пользователей
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():

    users = User.query.all()
    edit_user_id = request.args.get('edit')
    edit_user = User.query.get(edit_user_id) if edit_user_id else None
    return render_template('admin/users.html', users=users, edit_user=edit_user)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    login = request.form['login']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    full_name = request.form.get('full_name')
    email = request.form.get('email')

    # Проверка совпадения паролей
    if password != confirm_password:
        flash("Пароли не совпадают", "error")
        return redirect(url_for('admin_users'))

    # Проверка на уникальность логина и email
    if User.query.filter_by(login=login).first():
        flash("Логин уже используется", "error")
        return redirect(url_for('admin_users'))

    if User.query.filter_by(email=email).first():
        flash("Email уже используется", "error")
        return redirect(url_for('admin_users'))

    # Создание пользователя с хешированием пароля
    new_user = User(login=login, full_name=full_name, email=email)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    flash("Пользователь успешно добавлен", "success")
    return redirect(url_for('admin_users'))


# Обработка формы редактирования
@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.login = request.form.get('login')
        user.email = request.form.get('email')
        user.full_name = request.form.get('full_name')
        user.phone = request.form.get('phone')
        user.address = request.form.get('address')
        user.bee_coins = int(request.form.get('bee_coins') or 0)
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin_users'))
    return redirect(url_for('admin_users', edit=user_id))

# Удаление пользователя
@app.route('/admin/users/delete/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role_id == 1:
        flash('Cannot delete an admin user.', 'danger')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin_users'))




@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():

    orders = Order.query.order_by(Order.created_at.desc()).all()
    users = User.query.all()
    return render_template('admin/orders.html', orders=orders, users=users)

@app.route('/admin/orders/export')
@login_required
@admin_required
def export_orders_csv():
    import csv
    from io import StringIO


    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order ID', 'User', 'Total Amount', 'Created At', 'Items'])

    orders = Order.query.all()
    for order in orders:
        items_str = '; '.join([f"{item.product.name} × {item.quantity}" for item in order.items])
        writer.writerow([order.id, order.user.login,order.user.full_name, order.total_amount, order.created_at, items_str])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=orders.csv"
    response.headers["Content-type"] = "text/csv"
    return response


@app.route('/admin/orders/edit/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def edit_order(order_id):
    order = Order.query.get_or_404(order_id)

    # Обновление пользователя заказа
    new_user_id = int(request.form.get('user_id', order.user_id))
    order.user_id = new_user_id

    # Перерасчет суммы заказа
    total = Decimal('0.00')
    for item in order.items:
        quantity_field = f'quantity_{item.id}'
        new_quantity = int(request.form.get(quantity_field, item.quantity))

        if new_quantity < 1:
            flash("Количество товара должно быть >= 1", "danger")
            return redirect(url_for('admin_orders'))

        item.quantity = new_quantity
        item.price = item.product.price * new_quantity
        total += item.price

    order.total_amount = total
    db.session.commit()
    flash(f'Заказ #{order.id} успешно обновлён.', 'success')
    return redirect(url_for('admin_orders'))


# Админ: удаление заказа
@app.route('/admin/orders/delete/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)

    # Удаляем сначала дочерние OrderItems
    for item in order.items:
        db.session.delete(item)

    db.session.delete(order)
    db.session.commit()
    flash(f'Заказ #{order.id} удалён.', 'info')
    return redirect(url_for('admin_orders'))

if __name__ == '__main__':
    app.run()
