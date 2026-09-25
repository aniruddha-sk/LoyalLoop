import os,re
import psycopg
from functools import wraps
from dotenv import load_dotenv
from flask import Flask,render_template,request,redirect,url_for,flash,session, jsonify, abort
from werkzeug.security import generate_password_hash,check_password_hash
import io
import qrcode
from flask import send_file
from functools import wraps
from flask import session, redirect, url_for, flash
import secrets
load_dotenv()

app=Flask(__name__)
app.config["SECRET_KEY"]=os.getenv("SECRET_KEY")

def get_db_connection():
    try:
        return psycopg.connect(host=os.getenv("DB_HOST"),port=os.getenv("DB_PORT"),dbname=os.getenv("DB_NAME"),user=os.getenv("DB_USER"),password=os.getenv("DB_PASSWORD"))
    except Exception as e:
        print("\n❌ PostgreSQL Connection Failed!")
        print("Error:",e)
        return None


# ============================================================
# INPUT HELPERS
# ============================================================

def clean_text(value, max_length=None):
    """
    Safely clean user-provided text.
    """

    if value is None:
        return ""

    value = str(value).strip()

    if max_length:
        value = value[:max_length]

    return value


def normalize_email(email):
    """
    Normalize email.
    """

    return clean_text(
        email,
        150
    ).lower()


def normalize_phone(phone):
    """
    Normalize phone number.
    """

    phone = clean_text(
        phone,
        20
    )

    return re.sub(
        r"[^0-9+]",
        "",
        phone
    )


def owner_required(view_function):
    @wraps(view_function)
    def wrapped_view(*args,**kwargs):
        if session.get("user_type")!="owner":
            flash("Please login to continue.","error")
            return redirect(url_for("owner_login"))
        return view_function(*args,**kwargs)
    return wrapped_view

@app.route("/")
def home():
    if session.get("user_type")=="owner":
        return redirect(url_for("owner_dashboard"))
    return redirect(url_for("owner_login"))

@app.route("/owner/register",methods=["GET","POST"])
def owner_register():
    if request.method=="POST":
        full_name=request.form.get("full_name","").strip()
        email=request.form.get("email","").strip().lower()
        phone=request.form.get("phone","").strip()
        password=request.form.get("password","")

        if not full_name or not email or not phone or not password:
            flash("Please fill all fields.","error")
            return redirect(url_for("owner_register"))

        if len(password)<8:
            flash("Password must contain at least 8 characters.","error")
            return redirect(url_for("owner_register"))

        connection=get_db_connection()
        if not connection:
            flash("Database connection failed.","error")
            return redirect(url_for("owner_register"))

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id FROM owners WHERE email=%s",(email,))
                if cursor.fetchone():
                    flash("An account with this email already exists.","error")
                    return redirect(url_for("owner_login"))

                cursor.execute("SELECT id FROM owners WHERE phone=%s",(phone,))
                if cursor.fetchone():
                    flash("An account with this mobile number already exists.","error")
                    return redirect(url_for("owner_register"))

                password_hash=generate_password_hash(password)
                cursor.execute("""INSERT INTO owners(full_name,email,phone,password_hash) VALUES(%s,%s,%s,%s) RETURNING id""",(full_name,email,phone,password_hash))
                cursor.fetchone()
            connection.commit()
            flash("Account created successfully! Please login.","success")
            return redirect(url_for("owner_login"))
        except Exception as e:
            connection.rollback()
            print("Owner registration error:",e)
            flash("Something went wrong. Please try again.","error")
            return redirect(url_for("owner_register"))
        finally:
            connection.close()

    return render_template("auth/owner_register.html")

@app.route("/owner/login",methods=["GET","POST"])
def owner_login():
    if request.method=="POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")

        if not email or not password:
            flash("Please enter email and password.","error")
            return redirect(url_for("owner_login"))

        connection=get_db_connection()
        if not connection:
            flash("Database connection failed.","error")
            return redirect(url_for("owner_login"))

        try:
            with connection.cursor() as cursor:
                cursor.execute("""SELECT id,full_name,email,password_hash,is_active FROM owners WHERE email=%s""",(email,))
                owner=cursor.fetchone()

                if not owner:
                    flash("Invalid email or password.","error")
                    return redirect(url_for("owner_login"))

                owner_id,full_name,owner_email,password_hash,is_active=owner

                if not is_active:
                    flash("Your account is currently inactive.","error")
                    return redirect(url_for("owner_login"))

                if not check_password_hash(password_hash,password):
                    flash("Invalid email or password.","error")
                    return redirect(url_for("owner_login"))

                session.clear()
                session["owner_id"]=str(owner_id)
                session["owner_name"]=full_name
                session["owner_email"]=owner_email
                session["user_type"]="owner"

                cursor.execute("UPDATE owners SET last_login_at=CURRENT_TIMESTAMP WHERE id=%s",(owner_id,))
            connection.commit()
            flash("Welcome back! 👋","success")
            return redirect(url_for("owner_dashboard"))
        except Exception as e:
            connection.rollback()
            print("Owner login error:",e)
            flash("Something went wrong. Please try again.","error")
            return redirect(url_for("owner_login"))
        finally:
            connection.close()

    return render_template("auth/owner_login.html")

@app.route("/owner/setup-business",methods=["GET","POST"])
@owner_required
def setup_business():
    owner_id=session.get("owner_id")

    connection=get_db_connection()
    if not connection:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_dashboard"))

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM businesses WHERE owner_id=%s LIMIT 1",(owner_id,))
            existing_business=cursor.fetchone()

            if existing_business and request.method=="GET":
                session["business_id"]=str(existing_business[0])
                return redirect(url_for("owner_dashboard"))

        if request.method=="POST":
            business_name=request.form.get("business_name","").strip()
            business_type=request.form.get("business_type","").strip()
            phone=request.form.get("phone","").strip()
            email=request.form.get("email","").strip().lower()
            address=request.form.get("address","").strip()
            city=request.form.get("city","").strip()
            state=request.form.get("state","").strip()
            pincode=request.form.get("pincode","").strip()
            instagram_url=request.form.get("instagram_url","").strip()
            google_review_url=request.form.get("google_review_url","").strip()
            whatsapp_number=request.form.get("whatsapp_number","").strip()

            if not business_name or not business_type or not city:
                flash("Business name, type and city are required.","error")
                return redirect(url_for("setup_business"))

            with connection.cursor() as cursor:
                cursor.execute("""SELECT id FROM businesses WHERE owner_id=%s LIMIT 1""",(owner_id,))
                if cursor.fetchone():
                    flash("You already have a business.","error")
                    return redirect(url_for("owner_dashboard"))

                cursor.execute("""SELECT 'LL'||UPPER(SUBSTRING(MD5(RANDOM()::TEXT) FROM 1 FOR 10))""")
                business_code=cursor.fetchone()[0]

                slug_base=re.sub(r"[^a-z0-9]+","-",business_name.lower()).strip("-") or "business"
                slug=slug_base
                counter=1

                while True:
                    cursor.execute("SELECT id FROM businesses WHERE slug=%s",(slug,))
                    if not cursor.fetchone():
                        break
                    slug=f"{slug_base}-{counter}"
                    counter+=1

                cursor.execute("""INSERT INTO businesses(owner_id,business_name,business_code,slug,description,phone,email,address,city,state,country,pincode,instagram_url,google_review_url,whatsapp_number) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'India',%s,%s,%s,%s) RETURNING id""",(owner_id,business_name,business_code,slug,business_type,phone or None,email or None,address or None,city,state or None,pincode or None,instagram_url or None,google_review_url or None,whatsapp_number or None))
                business_id=cursor.fetchone()[0]

            connection.commit()
            session["business_id"]=str(business_id)
            session["business_name"]=business_name
            flash("Your business is ready! 🎉","success")
            return redirect(url_for("owner_dashboard"))

        return render_template("owner/setup_business.html")

    except Exception as e:
        connection.rollback()
        print("Business setup error:",e)
        flash("Unable to create business. Please try again.","error")
        return redirect(url_for("setup_business"))
    finally:
        connection.close()

@app.route("/owner/dashboard")
@owner_required
def owner_dashboard():
    owner_id=session.get("owner_id")
    connection=get_db_connection()

    if not connection:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_login"))

    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT id,business_name,business_code,city,state,status FROM businesses WHERE owner_id=%s ORDER BY created_at ASC LIMIT 1""",(owner_id,))
            business=cursor.fetchone()

            if not business:
                return redirect(url_for("setup_business"))

            business_id,business_name,business_code,city,state,business_status=business
            session["business_id"]=str(business_id)
            session["business_name"]=business_name

            cursor.execute("SELECT COUNT(*) FROM customers WHERE business_id=%s",(business_id,))
            total_customers=cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM orders WHERE business_id=%s",(business_id,))
            total_orders=cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM orders WHERE business_id=%s AND created_at::DATE=CURRENT_DATE",(business_id,))
            today_orders=cursor.fetchone()[0]

            cursor.execute("SELECT COALESCE(SUM(total_amount),0) FROM orders WHERE business_id=%s AND status='delivered'",(business_id,))
            total_revenue=cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM orders WHERE business_id=%s AND status='pending'",(business_id,))
            pending_orders=cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM menu_items WHERE business_id=%s AND is_active=TRUE",(business_id,))
            total_menu_items=cursor.fetchone()[0]

            cursor.execute("""SELECT COUNT(*) FROM customers WHERE business_id=%s AND last_visit_at>=CURRENT_TIMESTAMP-INTERVAL '30 days'""",(business_id,))
            active_customers=cursor.fetchone()[0]

            cursor.execute("""SELECT COUNT(*) FROM reward_claims WHERE business_id=%s AND status='claimed'""",(business_id,))
            pending_rewards=cursor.fetchone()[0]

        return render_template("owner/dashboard.html",business_name=business_name,business_code=business_code,city=city,state=state,business_status=business_status,total_customers=total_customers,total_orders=total_orders,today_orders=today_orders,total_revenue=total_revenue,pending_orders=pending_orders,total_menu_items=total_menu_items,active_customers=active_customers,pending_rewards=pending_rewards)

    except Exception as e:
        print("\n================ DASHBOARD ERROR ================")
        print(repr(e))
        print("=================================================\n")
        flash(f"Dashboard Error: {e}","error")
        return redirect(url_for("owner_login"))
    finally:
        connection.close()



@app.route("/owner/business/profile",methods=["GET","POST"])
@owner_required
def business_profile():
    conn=get_db_connection(); cur=conn.cursor()
    if request.method=="POST":
        business_name=request.form.get("business_name","").strip()
        phone=request.form.get("phone","").strip()
        email=request.form.get("email","").strip()
        address=request.form.get("address","").strip()
        city=request.form.get("city","").strip()
        state=request.form.get("state","").strip()
        pincode=request.form.get("pincode","").strip()
        instagram_url=request.form.get("instagram_url","").strip()
        google_review_url=request.form.get("google_review_url","").strip()
        whatsapp_number=request.form.get("whatsapp_number","").strip()
        if not business_name or not phone or not city or not state or not pincode:
            flash("Please fill all required fields.","error"); cur.close(); conn.close(); return redirect(url_for("business_profile"))
        cur.execute("""UPDATE businesses SET business_name=%s,phone=%s,email=%s,address=%s,city=%s,state=%s,pincode=%s,instagram_url=%s,google_review_url=%s,whatsapp_number=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s""",(business_name,phone,email,address,city,state,pincode,instagram_url or None,google_review_url or None,whatsapp_number or None,session["business_id"]))
        conn.commit(); session["business_name"]=business_name
        flash("Business profile updated successfully!","success")
        cur.close(); conn.close(); return redirect(url_for("business_profile"))
    cur.execute("""SELECT id,business_name,description,phone,email,address,city,state,pincode,instagram_url,google_review_url,whatsapp_number,business_code,slug,status FROM businesses WHERE id=%s""",(session["business_id"],))
    business=cur.fetchone(); cur.close(); conn.close()
    if not business: flash("Business not found.","error"); return redirect(url_for("owner_dashboard"))
    return render_template("owner/business/profile.html",business=business)


@app.route("/owner/business/settings",methods=["GET","POST"])
@owner_required
def business_settings():
    conn=get_db_connection(); cur=conn.cursor()
    if request.method=="POST":
        timezone=request.form.get("timezone","Asia/Kolkata").strip()
        currency=request.form.get("currency","INR").strip()
        status=request.form.get("status","active").strip()
        if status not in ("active","inactive","suspended"): status="active"
        cur.execute("UPDATE businesses SET timezone=%s,currency=%s,status=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s",(timezone,currency,status,session["business_id"]))
        conn.commit(); flash("Business settings updated successfully!","success")
        cur.close(); conn.close(); return redirect(url_for("business_settings"))
    cur.execute("SELECT business_name,timezone,currency,status,business_code,slug FROM businesses WHERE id=%s",(session["business_id"],))
    business=cur.fetchone(); cur.close(); conn.close()
    return render_template("owner/business/settings.html",business=business)

@app.route("/owner/menu")
@owner_required
def owner_menu():
    conn=get_db_connection(); cur=conn.cursor()
    cur.execute("SELECT id,category_name,description,display_order FROM menu_categories WHERE business_id=%s AND is_active=TRUE ORDER BY display_order,category_name",(session["business_id"],))
    categories=cur.fetchall()
    cur.execute("""SELECT m.id,m.item_name,m.description,m.price,m.image_url,m.is_available,c.category_name AS category_name FROM menu_items m LEFT JOIN menu_categories c ON c.id=m.category_id AND c.is_active=TRUE WHERE m.business_id=%s AND m.is_active=TRUE ORDER BY c.display_order,c.category_name,m.display_order,m.item_name""",(session["business_id"],))
    items=cur.fetchall(); cur.close(); conn.close()
    return render_template("owner/menu/menu.html",categories=categories,items=items)


@app.route("/owner/menu/category/add",methods=["POST"])
@owner_required
def add_menu_category():
    name=request.form.get("name","").strip()
    description=request.form.get("description","").strip()
    if not name:
        flash("Category name is required.","error")
        return redirect(url_for("owner_menu"))
    conn=get_db_connection(); cur=conn.cursor()
    cur.execute("SELECT COALESCE(MAX(display_order),0)+1 FROM menu_categories WHERE business_id=%s",(session["business_id"],))
    display_order=cur.fetchone()[0]
    cur.execute("INSERT INTO menu_categories(business_id,category_name,description,display_order,is_active) VALUES(%s,%s,%s,%s,TRUE)",(session["business_id"],name,description or None,display_order))
    conn.commit(); cur.close(); conn.close()
    flash("Menu category added successfully!","success")
    return redirect(url_for("owner_menu"))


@app.route("/owner/menu/category/<category_id>/edit",methods=["GET","POST"])
@owner_required
def edit_menu_category(category_id):
    conn=get_db_connection(); cur=conn.cursor()
    if request.method=="POST":
        name=request.form.get("name","").strip()
        description=request.form.get("description","").strip()
        if not name:
            flash("Category name is required.","error")
            cur.close(); conn.close()
            return redirect(url_for("edit_menu_category",category_id=category_id))
        cur.execute("UPDATE menu_categories SET category_name=%s,description=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s AND business_id=%s AND is_active=TRUE",(name,description or None,category_id,session["business_id"]))
        updated=cur.rowcount
        conn.commit(); cur.close(); conn.close()
        flash("Category updated successfully!" if updated else "Category not found.","success" if updated else "error")
        return redirect(url_for("owner_menu"))
    cur.execute("SELECT id,category_name,description FROM menu_categories WHERE id=%s AND business_id=%s AND is_active=TRUE",(category_id,session["business_id"]))
    category=cur.fetchone(); cur.close(); conn.close()
    if not category:
        flash("Category not found.","error")
        return redirect(url_for("owner_menu"))
    return render_template("owner/menu/edit_category.html",category=category)


@app.route("/owner/menu/category/<category_id>/delete",methods=["POST"])
@owner_required
def delete_menu_category(category_id):
    conn=get_db_connection(); cur=conn.cursor()
    cur.execute("UPDATE menu_categories SET is_active=FALSE,updated_at=CURRENT_TIMESTAMP WHERE id=%s AND business_id=%s AND is_active=TRUE",(category_id,session["business_id"]))
    deleted=cur.rowcount
    if deleted:
        cur.execute("UPDATE menu_items SET is_active=FALSE,is_available=FALSE,updated_at=CURRENT_TIMESTAMP WHERE category_id=%s AND business_id=%s",(category_id,session["business_id"]))
    conn.commit(); cur.close(); conn.close()
    flash("Category deleted successfully!" if deleted else "Category not found.","success" if deleted else "error")
    return redirect(url_for("owner_menu"))


@app.route("/owner/menu/item/add",methods=["GET","POST"])
@owner_required
def add_menu_item():
    conn=get_db_connection(); cur=conn.cursor()
    if request.method=="POST":
        category_id=request.form.get("category_id") or None
        name=request.form.get("name","").strip()
        description=request.form.get("description","").strip()
        price=request.form.get("price","").strip()
        image_url=request.form.get("image_url","").strip()
        if not name or not price:
            flash("Item name and price are required.","error")
            cur.close(); conn.close()
            return redirect(url_for("add_menu_item"))
        try:
            price=float(price)
        except ValueError:
            flash("Please enter a valid price.","error")
            cur.close(); conn.close()
            return redirect(url_for("add_menu_item"))
        if category_id:
            cur.execute("SELECT id FROM menu_categories WHERE id=%s AND business_id=%s AND is_active=TRUE",(category_id,session["business_id"]))
            if not cur.fetchone():
                flash("Selected category is invalid.","error")
                cur.close(); conn.close()
                return redirect(url_for("add_menu_item"))
        cur.execute("SELECT COALESCE(MAX(display_order),0)+1 FROM menu_items WHERE business_id=%s",(session["business_id"],))
        display_order=cur.fetchone()[0]
        cur.execute("INSERT INTO menu_items(business_id,category_id,item_name,description,image_url,price,is_available,is_active,display_order) VALUES(%s,%s,%s,%s,%s,%s,TRUE,TRUE,%s)",(session["business_id"],category_id,name,description or None,image_url or None,price,display_order))
        conn.commit(); cur.close(); conn.close()
        flash("Menu item added successfully!","success")
        return redirect(url_for("owner_menu"))
    cur.execute("SELECT id,category_name FROM menu_categories WHERE business_id=%s AND is_active=TRUE ORDER BY display_order,category_name",(session["business_id"],))
    categories=cur.fetchall(); cur.close(); conn.close()
    return render_template("owner/menu/add_item.html",categories=categories)


@app.route("/owner/menu/item/<item_id>/edit",methods=["GET","POST"])
@owner_required
def edit_menu_item(item_id):
    conn=get_db_connection(); cur=conn.cursor()
    if request.method=="POST":
        category_id=request.form.get("category_id") or None
        name=request.form.get("name","").strip()
        description=request.form.get("description","").strip()
        price=request.form.get("price","").strip()
        image_url=request.form.get("image_url","").strip()
        if not name or not price:
            flash("Item name and price are required.","error")
            cur.close(); conn.close()
            return redirect(url_for("edit_menu_item",item_id=item_id))
        try:
            price=float(price)
        except ValueError:
            flash("Please enter a valid price.","error")
            cur.close(); conn.close()
            return redirect(url_for("edit_menu_item",item_id=item_id))
        if category_id:
            cur.execute("SELECT id FROM menu_categories WHERE id=%s AND business_id=%s AND is_active=TRUE",(category_id,session["business_id"]))
            if not cur.fetchone():
                flash("Selected category is invalid.","error")
                cur.close(); conn.close()
                return redirect(url_for("edit_menu_item",item_id=item_id))
        cur.execute("""UPDATE menu_items SET category_id=%s,item_name=%s,description=%s,image_url=%s,price=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s AND business_id=%s AND is_active=TRUE""",(category_id,name,description or None,image_url or None,price,item_id,session["business_id"]))
        updated=cur.rowcount
        conn.commit(); cur.close(); conn.close()
        flash("Menu item updated successfully!" if updated else "Menu item not found.","success" if updated else "error")
        return redirect(url_for("owner_menu"))
    cur.execute("SELECT id,item_name,description,image_url,price,category_id FROM menu_items WHERE id=%s AND business_id=%s AND is_active=TRUE",(item_id,session["business_id"]))
    item=cur.fetchone()
    if not item:
        cur.close(); conn.close()
        flash("Menu item not found.","error")
        return redirect(url_for("owner_menu"))
    cur.execute("SELECT id,category_name FROM menu_categories WHERE business_id=%s AND is_active=TRUE ORDER BY display_order,category_name",(session["business_id"],))
    categories=cur.fetchall(); cur.close(); conn.close()
    return render_template("owner/menu/edit_item.html",item=item,categories=categories)


@app.route("/owner/menu/item/<item_id>/toggle",methods=["POST"])
@owner_required
def toggle_menu_item(item_id):
    conn=get_db_connection(); cur=conn.cursor()
    cur.execute("UPDATE menu_items SET is_available=NOT is_available,updated_at=CURRENT_TIMESTAMP WHERE id=%s AND business_id=%s AND is_active=TRUE RETURNING is_available",(item_id,session["business_id"]))
    result=cur.fetchone(); conn.commit(); cur.close(); conn.close()
    flash("Item availability updated.","success" if result else "error")
    if not result:
        flash("Menu item not found.","error")
    return redirect(url_for("owner_menu"))


@app.route("/owner/menu/item/<item_id>/delete",methods=["POST"])
@owner_required
def delete_menu_item(item_id):
    conn=get_db_connection(); cur=conn.cursor()
    cur.execute("UPDATE menu_items SET is_active=FALSE,is_available=FALSE,updated_at=CURRENT_TIMESTAMP WHERE id=%s AND business_id=%s AND is_active=TRUE",(item_id,session["business_id"]))
    deleted=cur.rowcount
    conn.commit(); cur.close(); conn.close()
    flash("Menu item deleted successfully!" if deleted else "Menu item not found.","success" if deleted else "error")
    return redirect(url_for("owner_menu"))




# ============================================================
# ORDERS MANAGEMENT
# ============================================================

@app.route("/owner/orders")
@owner_required
def owner_orders():
    status=request.args.get("status","all").strip().lower()
    search=request.args.get("search","").strip()

    conn=get_db_connection()
    cur=conn.cursor()

    query="""
        SELECT
            o.id,
            o.order_number,
            o.status,
            o.total_amount,
            o.payment_status,
            o.created_at,
            o.delivered_at,
            c.full_name,
            c.phone,
            COALESCE(SUM(oi.quantity),0) AS total_items
        FROM orders o
        JOIN customers c
            ON c.id=o.customer_id
            AND c.business_id=o.business_id
        LEFT JOIN order_items oi
            ON oi.order_id=o.id
            AND oi.business_id=o.business_id
        WHERE o.business_id=%s
    """

    params=[session["business_id"]]

    if status in ("pending","confirmed","preparing","ready","delivered","cancelled"):
        query+=" AND o.status=%s"
        params.append(status)

    if search:
        query+=" AND (CAST(o.order_number AS TEXT) ILIKE %s OR c.full_name ILIKE %s OR c.phone ILIKE %s)"
        search_value=f"%{search}%"
        params.extend([search_value,search_value,search_value])

    query+="""
        GROUP BY
            o.id,
            o.order_number,
            o.status,
            o.total_amount,
            o.payment_status,
            o.created_at,
            o.delivered_at,
            c.full_name,
            c.phone
        ORDER BY o.created_at DESC
    """

    cur.execute(query,params)
    orders=cur.fetchall()

    cur.execute("""
        SELECT
            COUNT(*),
            COUNT(*) FILTER (WHERE status='pending'),
            COUNT(*) FILTER (WHERE status='confirmed'),
            COUNT(*) FILTER (WHERE status='preparing'),
            COUNT(*) FILTER (WHERE status='ready'),
            COUNT(*) FILTER (WHERE status='delivered'),
            COUNT(*) FILTER (WHERE status='cancelled')
        FROM orders
        WHERE business_id=%s
    """,(session["business_id"],))

    counts=cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "owner/orders/orders.html",
        orders=orders,
        counts=counts,
        status=status,
        search=search
    )


@app.route("/owner/orders/<order_id>")
@owner_required
def order_details(order_id):
    conn=get_db_connection()
    cur=conn.cursor()

    cur.execute("""
        SELECT
            o.id,
            o.order_number,
            o.status,
            o.subtotal,
            o.discount_amount,
            o.tax_amount,
            o.delivery_charge,
            o.total_amount,
            o.payment_status,
            o.customer_note,
            o.confirmed_at,
            o.preparing_at,
            o.ready_at,
            o.delivered_at,
            o.cancelled_at,
            o.created_at,
            o.updated_at,
            c.id,
            c.full_name,
            c.email,
            c.phone
        FROM orders o
        JOIN customers c
            ON c.id=o.customer_id
            AND c.business_id=o.business_id
        WHERE o.id=%s
        AND o.business_id=%s
    """,(order_id,session["business_id"]))

    order=cur.fetchone()

    if not order:
        cur.close()
        conn.close()
        flash("Order not found.","error")
        return redirect(url_for("owner_orders"))

    cur.execute("""
        SELECT
            id,
            item_name,
            unit_price,
            quantity,
            total_price
        FROM order_items
        WHERE order_id=%s
        AND business_id=%s
        ORDER BY created_at ASC
    """,(order_id,session["business_id"]))

    items=cur.fetchall()

    cur.execute("""
        SELECT
            id,
            old_status,
            new_status,
            changed_at,
            note
        FROM order_status_history
        WHERE order_id=%s
        AND business_id=%s
        ORDER BY changed_at DESC
    """,(order_id,session["business_id"]))

    history=cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "owner/orders/order_details.html",
        order=order,
        items=items,
        history=history
    )


@app.route("/owner/orders/<order_id>/status",methods=["POST"])
@owner_required
def update_order_status(order_id):
    new_status=request.form.get("status","").strip().lower()
    note=request.form.get("note","").strip()

    allowed_statuses={
        "pending",
        "confirmed",
        "preparing",
        "ready",
        "delivered",
        "cancelled"
    }

    if new_status not in allowed_statuses:
        flash("Invalid order status.","error")
        return redirect(url_for("order_details",order_id=order_id))

    valid_flow={
        "pending":["confirmed","cancelled"],
        "confirmed":["preparing","cancelled"],
        "preparing":["ready","cancelled"],
        "ready":["delivered","cancelled"],
        "delivered":[],
        "cancelled":[]
    }

    conn=get_db_connection()
    cur=conn.cursor()

    try:
        cur.execute("""
            SELECT
                id,
                customer_id,
                status,
                total_amount
            FROM orders
            WHERE id=%s
            AND business_id=%s
            FOR UPDATE
        """,(order_id,session["business_id"]))

        order=cur.fetchone()

        if not order:
            flash("Order not found.","error")
            conn.rollback()
            return redirect(url_for("owner_orders"))

        old_status=order[2]
        customer_id=order[1]
        total_amount=order[3]

        if old_status==new_status:
            flash("Order is already in this status.","error")
            conn.rollback()
            return redirect(url_for("order_details",order_id=order_id))

        if new_status not in valid_flow.get(old_status,[]):
            flash(
                f"Cannot change order from {old_status.title()} to {new_status.title()}.",
                "error"
            )
            conn.rollback()
            return redirect(url_for("order_details",order_id=order_id))

        if new_status=="confirmed":
            cur.execute("""
                UPDATE orders
                SET status=%s,
                    confirmed_at=COALESCE(confirmed_at,CURRENT_TIMESTAMP),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
                AND business_id=%s
            """,(new_status,order_id,session["business_id"]))

        elif new_status=="preparing":
            cur.execute("""
                UPDATE orders
                SET status=%s,
                    preparing_at=COALESCE(preparing_at,CURRENT_TIMESTAMP),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
                AND business_id=%s
            """,(new_status,order_id,session["business_id"]))

        elif new_status=="ready":
            cur.execute("""
                UPDATE orders
                SET status=%s,
                    ready_at=COALESCE(ready_at,CURRENT_TIMESTAMP),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
                AND business_id=%s
            """,(new_status,order_id,session["business_id"]))

        elif new_status=="delivered":
            cur.execute("""
                UPDATE orders
                SET status=%s,
                    delivered_at=COALESCE(delivered_at,CURRENT_TIMESTAMP),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
                AND business_id=%s
            """,(new_status,order_id,session["business_id"]))

        elif new_status=="cancelled":
            cur.execute("""
                UPDATE orders
                SET status=%s,
                    cancelled_at=COALESCE(cancelled_at,CURRENT_TIMESTAMP),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s
                AND business_id=%s
            """,(new_status,order_id,session["business_id"]))

        cur.execute("""
            INSERT INTO order_status_history
            (
                business_id,
                order_id,
                old_status,
                new_status,
                note
            )
            VALUES(%s,%s,%s,%s,%s)
        """,(
            session["business_id"],
            order_id,
            old_status,
            new_status,
            note or None
        ))

        loyalty_message=None

        if new_status=="delivered":

            cur.execute("""
                SELECT
                    minimum_order_amount,
                    stamps_per_eligible_order,
                    is_active
                FROM loyalty_settings
                WHERE business_id=%s
                LIMIT 1
            """,(session["business_id"],))

            loyalty=cur.fetchone()

            if loyalty:
                minimum_amount=loyalty[0]
                stamps=loyalty[1]
                loyalty_active=loyalty[2]

                if loyalty_active and total_amount>=minimum_amount:

                    cur.execute("""
                        SELECT id
                        FROM loyalty_transactions
                        WHERE business_id=%s
                        AND order_id=%s
                        AND transaction_type='order_stamp'
                        LIMIT 1
                    """,(session["business_id"],order_id))

                    existing_stamp=cur.fetchone()

                    if not existing_stamp:

                        cur.execute("""
                            INSERT INTO loyalty_stamps
                            (
                                business_id,
                                customer_id,
                                order_id,
                                stamp_count,
                                reason
                            )
                            VALUES(%s,%s,%s,%s,%s)
                        """,(
                            session["business_id"],
                            customer_id,
                            order_id,
                            stamps,
                            "Eligible delivered order"
                        ))

                        cur.execute("""
                            INSERT INTO loyalty_transactions
                            (
                                business_id,
                                customer_id,
                                order_id,
                                transaction_type,
                                stamps,
                                description
                            )
                            VALUES(%s,%s,%s,%s,%s,%s)
                        """,(
                            session["business_id"],
                            customer_id,
                            order_id,
                            "order_stamp",
                            stamps,
                            "Loyalty stamp earned from delivered order"
                        ))

                        loyalty_message=f"{stamps} loyalty stamp(s) added!"

                    else:
                        loyalty_message="Loyalty stamp already exists for this order."

                else:
                    loyalty_message="This order is not eligible for loyalty stamp."

            else:
                loyalty_message="Loyalty settings are not configured yet."

        conn.commit()

        if new_status=="delivered":
            if loyalty_message:
                flash(f"Order delivered successfully. {loyalty_message}","success")
            else:
                flash("Order delivered successfully.","success")
        elif new_status=="cancelled":
            flash("Order cancelled successfully. No loyalty stamp added.","success")
        else:
            flash(f"Order status changed to {new_status.title()}.","success")

    except Exception as e:
        conn.rollback()
        flash(f"Unable to update order: {e}","error")

    finally:
        cur.close()
        conn.close()

    return redirect(url_for("order_details",order_id=order_id))



# ============================================================
# CUSTOMERS MANAGEMENT
# ============================================================

@app.route("/owner/customers")
@owner_required
def owner_customers():
    search=request.args.get("search","").strip()
    conn=get_db_connection()
    cur=conn.cursor()

    query="""
        SELECT id,full_name,email,phone,is_active,total_visits,
               total_orders,total_spent,last_visit_at,last_order_at,created_at
        FROM customers
        WHERE business_id=%s
    """
    params=[session["business_id"]]

    if search:
        query+=" AND (full_name ILIKE %s OR phone ILIKE %s OR COALESCE(email,'') ILIKE %s)"
        value=f"%{search}%"
        params.extend([value,value,value])

    query+=" ORDER BY last_order_at DESC NULLS LAST,created_at DESC"

    cur.execute(query,params)
    customers=cur.fetchall()

    cur.execute("""
        SELECT
            COUNT(*),
            COUNT(*) FILTER(WHERE is_active=TRUE),
            COALESCE(SUM(total_orders),0),
            COALESCE(SUM(total_spent),0)
        FROM customers
        WHERE business_id=%s
    """,(session["business_id"],))
    stats=cur.fetchone()

    cur.close()
    conn.close()

    return render_template(
        "owner/customers/customers.html",
        customers=customers,
        stats=stats,
        search=search
    )


@app.route("/owner/customers/<customer_id>")
@owner_required
def customer_details(customer_id):
    conn=get_db_connection()
    cur=conn.cursor()

    cur.execute("""
        SELECT
            id,full_name,email,phone,is_active,
            total_visits,total_orders,total_spent,
            last_visit_at,last_order_at,created_at
        FROM customers
        WHERE id=%s AND business_id=%s
    """,(customer_id,session["business_id"]))

    customer=cur.fetchone()

    if not customer:
        cur.close()
        conn.close()
        flash("Customer not found.","error")
        return redirect(url_for("owner_customers"))

    cur.execute("""
        SELECT
            o.id,o.order_number,o.status,o.total_amount,
            o.payment_status,o.created_at
        FROM orders o
        WHERE o.customer_id=%s
        AND o.business_id=%s
        ORDER BY o.created_at DESC
        LIMIT 10
    """,(customer_id,session["business_id"]))

    orders=cur.fetchall()

    cur.execute("""
        SELECT
            id,stamp_count,reason,created_at
        FROM loyalty_stamps
        WHERE customer_id=%s
        AND business_id=%s
        ORDER BY created_at DESC
        LIMIT 10
    """,(customer_id,session["business_id"]))

    stamps=cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "owner/customers/customer_details.html",
        customer=customer,
        orders=orders,
        stamps=stamps
    )



# ============================================================
# LOYALTY SETTINGS
# ============================================================

@app.route("/owner/loyalty/settings",methods=["GET","POST"])
@owner_required
def owner_loyalty_settings():

    business_id=session.get("business_id")

    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))

    conn=get_db_connection()

    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_dashboard"))

    try:

        with conn.cursor() as cur:

            if request.method=="POST":

                try:
                    minimum_order_amount=float(
                        request.form.get(
                            "minimum_order_amount",
                            0
                        )
                    )

                    stamps_per_eligible_order=int(
                        request.form.get(
                            "stamps_per_eligible_order",
                            0
                        )
                    )

                    reward_stamps_required=int(
                        request.form.get(
                            "reward_stamps_required",
                            0
                        )
                    )

                except ValueError:

                    flash(
                        "Please enter valid loyalty values.",
                        "error"
                    )

                    return redirect(
                        url_for("owner_loyalty_settings")
                    )

                is_active=(
                    request.form.get("is_active")
                    == "on"
                )

                if minimum_order_amount<0:

                    flash(
                        "Minimum order amount cannot be negative.",
                        "error"
                    )

                    return redirect(
                        url_for("owner_loyalty_settings")
                    )

                if stamps_per_eligible_order<=0:

                    flash(
                        "Stamps per order must be greater than zero.",
                        "error"
                    )

                    return redirect(
                        url_for("owner_loyalty_settings")
                    )

                if reward_stamps_required<=0:

                    flash(
                        "Required reward stamps must be greater than zero.",
                        "error"
                    )

                    return redirect(
                        url_for("owner_loyalty_settings")
                    )

                cur.execute(
                    """
                    INSERT INTO loyalty_settings
                    (
                        business_id,
                        minimum_order_amount,
                        stamps_per_eligible_order,
                        reward_stamps_required,
                        is_active
                    )
                    VALUES(%s,%s,%s,%s,%s)

                    ON CONFLICT (business_id)
                    DO UPDATE SET
                        minimum_order_amount=EXCLUDED.minimum_order_amount,
                        stamps_per_eligible_order=EXCLUDED.stamps_per_eligible_order,
                        reward_stamps_required=EXCLUDED.reward_stamps_required,
                        is_active=EXCLUDED.is_active,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        business_id,
                        minimum_order_amount,
                        stamps_per_eligible_order,
                        reward_stamps_required,
                        is_active
                    )
                )

                conn.commit()

                flash(
                    "Loyalty settings updated successfully! 🎉",
                    "success"
                )

                return redirect(
                    url_for("owner_loyalty_settings")
                )


            cur.execute(
                """
                SELECT
                    minimum_order_amount,
                    stamps_per_eligible_order,
                    reward_stamps_required,
                    is_active
                FROM loyalty_settings
                WHERE business_id=%s
                LIMIT 1
                """,
                (business_id,)
            )

            settings=cur.fetchone()

            cur.execute(
                """
                SELECT
                    business_name,
                    city,
                    business_code
                FROM businesses
                WHERE id=%s
                """,
                (business_id,)
            )

            business=cur.fetchone()

        return render_template(
            "owner/loyalty/loyalty_settings.html",
            settings=settings,
            business_name=business[0] if business else "Business",
            city=business[1] if business else "",
            business_code=business[2] if business else None,
            header_section="LOYALTY",
            header_title="Loyalty Settings"
        )

    except Exception as error:

        conn.rollback()

        app.logger.exception(
            "Loyalty settings error: %s",
            error
        )

        flash(
            "Unable to load loyalty settings.",
            "error"
        )

        return redirect(
            url_for("owner_dashboard")
        )

    finally:

        conn.close()


# ============================================================
# REWARDS LIST
# ============================================================

@app.route("/owner/loyalty/rewards")
@owner_required
def owner_rewards():

    business_id=session.get("business_id")

    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))

    conn=get_db_connection()

    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_dashboard"))

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    id,
                    reward_name,
                    description,
                    reward_value,
                    required_stamps,
                    validity_days,
                    status,
                    created_at
                FROM rewards
                WHERE business_id=%s
                ORDER BY created_at DESC
                """,
                (business_id,)
            )

            rewards=cur.fetchall()

            cur.execute(
                """
                SELECT COUNT(*)
                FROM rewards
                WHERE business_id=%s
                """,
                (business_id,)
            )

            total_rewards=cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(*)
                FROM rewards
                WHERE business_id=%s
                AND status='active'
                """,
                (business_id,)
            )

            active_rewards=cur.fetchone()[0]

            cur.execute(
                """
                SELECT reward_stamps_required
                FROM loyalty_settings
                WHERE business_id=%s
                LIMIT 1
                """,
                (business_id,)
            )

            loyalty=cur.fetchone()

            loyalty_required=(
                loyalty[0]
                if loyalty
                else 0
            )

            cur.execute(
                """
                SELECT
                    business_name,
                    city,
                    business_code
                FROM businesses
                WHERE id=%s
                """,
                (business_id,)
            )

            business=cur.fetchone()

        return render_template(
            "owner/loyalty/rewards.html",
            rewards=rewards,
            total_rewards=total_rewards,
            active_rewards=active_rewards,
            loyalty_required=loyalty_required,
            business_name=business[0] if business else "Business",
            city=business[1] if business else "",
            business_code=business[2] if business else None,
            header_section="LOYALTY",
            header_title="Rewards"
        )

    except Exception as error:

        app.logger.exception(
            "Rewards loading error: %s",
            error
        )

    except Exception as error:
        conn.rollback()
        print("REWARDS LOAD ERROR:",repr(error))
        flash(f"Unable to load rewards: {error}","error")
        return redirect(url_for("owner_dashboard"))

        return redirect(
            url_for("owner_dashboard")
        )

    finally:

        conn.close()


# ============================================================
# ADD REWARD
# ============================================================

@app.route(
    "/owner/loyalty/rewards/add",
    methods=["GET","POST"]
)
@owner_required
def add_reward():

    business_id=session.get("business_id")

    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))

    conn=get_db_connection()

    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_rewards"))

    try:

        if request.method=="POST":

            reward_name=request.form.get(
                "reward_name",
                ""
            ).strip()

            description=request.form.get(
                "description",
                ""
            ).strip()

            reward_value=request.form.get(
                "reward_value",
                ""
            ).strip()

            required_stamps=request.form.get(
                "required_stamps",
                ""
            ).strip()

            validity_days=request.form.get(
                "validity_days",
                ""
            ).strip()

            if not reward_name:

                flash(
                    "Reward name is required.",
                    "error"
                )

                return redirect(
                    url_for("add_reward")
                )

            try:

                required_stamps=int(
                    required_stamps
                )

            except ValueError:

                flash(
                    "Required stamps must be a valid number.",
                    "error"
                )

                return redirect(
                    url_for("add_reward")
                )

            if required_stamps<=0:

                flash(
                    "Required stamps must be greater than zero.",
                    "error"
                )

                return redirect(
                    url_for("add_reward")
                )

            if reward_value:

                try:
                    reward_value=float(
                        reward_value
                    )

                except ValueError:

                    flash(
                        "Reward value must be a valid number.",
                        "error"
                    )

                    return redirect(
                        url_for("add_reward")
                    )

                if reward_value<0:

                    flash(
                        "Reward value cannot be negative.",
                        "error"
                    )

                    return redirect(
                        url_for("add_reward")
                    )

            else:

                reward_value=None

            if validity_days:

                try:
                    validity_days=int(
                        validity_days
                    )

                except ValueError:

                    flash(
                        "Validity must be a valid number.",
                        "error"
                    )

                    return redirect(
                        url_for("add_reward")
                    )

                if validity_days<=0:

                    flash(
                        "Validity must be greater than zero.",
                        "error"
                    )

                    return redirect(
                        url_for("add_reward")
                    )

            else:

                validity_days=None


            with conn.cursor() as cur:

                cur.execute(
                    """
                    INSERT INTO rewards
                    (
                        business_id,
                        reward_name,
                        description,
                        reward_value,
                        required_stamps,
                        validity_days
                    )
                    VALUES(%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        business_id,
                        reward_name,
                        description or None,
                        reward_value,
                        required_stamps,
                        validity_days
                    )
                )

            conn.commit()

            flash(
                "Reward created successfully! 🎁",
                "success"
            )

            return redirect(
                url_for("owner_rewards")
            )


        with conn.cursor() as cur:

            cur.execute(
                """
                SELECT
                    business_name,
                    city,
                    business_code
                FROM businesses
                WHERE id=%s
                """,
                (business_id,)
            )

            business=cur.fetchone()

        return render_template(
            "owner/loyalty/add_reward.html",
            business_name=business[0] if business else "Business",
            city=business[1] if business else "",
            business_code=business[2] if business else None,
            header_section="LOYALTY",
            header_title="Add Reward"
        )

    except Exception as error:

        conn.rollback()

        app.logger.exception(
            "Add reward error: %s",
            error
        )

        flash(
            "Unable to create reward.",
            "error"
        )

        return redirect(
            url_for("owner_rewards")
        )

    finally:

        conn.close()


# ============================================================
# EDIT REWARD
# ============================================================

@app.route(
    "/owner/loyalty/rewards/<reward_id>/edit",
    methods=["GET","POST"]
)
@owner_required
def edit_reward(reward_id):

    business_id=session.get("business_id")

    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))

    conn=get_db_connection()

    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_rewards"))

    try:

        with conn.cursor() as cur:

            if request.method=="POST":

                reward_name=request.form.get(
                    "reward_name",
                    ""
                ).strip()

                description=request.form.get(
                    "description",
                    ""
                ).strip()

                reward_value=request.form.get(
                    "reward_value",
                    ""
                ).strip()

                required_stamps=request.form.get(
                    "required_stamps",
                    ""
                ).strip()

                validity_days=request.form.get(
                    "validity_days",
                    ""
                ).strip()

                if not reward_name:

                    flash(
                        "Reward name is required.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "edit_reward",
                            reward_id=reward_id
                        )
                    )

                try:

                    required_stamps=int(
                        required_stamps
                    )

                except ValueError:

                    flash(
                        "Required stamps must be a valid number.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "edit_reward",
                            reward_id=reward_id
                        )
                    )

                if required_stamps<=0:

                    flash(
                        "Required stamps must be greater than zero.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "edit_reward",
                            reward_id=reward_id
                        )
                    )

                if reward_value:

                    try:
                        reward_value=float(
                            reward_value
                        )

                    except ValueError:

                        flash(
                            "Reward value must be a valid number.",
                            "error"
                        )

                        return redirect(
                            url_for(
                                "edit_reward",
                                reward_id=reward_id
                            )
                        )

                    if reward_value<0:

                        flash(
                            "Reward value cannot be negative.",
                            "error"
                        )

                        return redirect(
                            url_for(
                                "edit_reward",
                                reward_id=reward_id
                            )
                        )

                else:

                    reward_value=None

                if validity_days:

                    try:
                        validity_days=int(
                            validity_days
                        )

                    except ValueError:

                        flash(
                            "Validity must be a valid number.",
                            "error"
                        )

                        return redirect(
                            url_for(
                                "edit_reward",
                                reward_id=reward_id
                            )
                        )

                    if validity_days<=0:

                        flash(
                            "Validity must be greater than zero.",
                            "error"
                        )

                        return redirect(
                            url_for(
                                "edit_reward",
                                reward_id=reward_id
                            )
                        )

                else:

                    validity_days=None


                cur.execute(
                    """
                    UPDATE rewards
                    SET
                        reward_name=%s,
                        description=%s,
                        reward_value=%s,
                        required_stamps=%s,
                        validity_days=%s,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                    AND business_id=%s
                    """,
                    (
                        reward_name,
                        description or None,
                        reward_value,
                        required_stamps,
                        validity_days,
                        reward_id,
                        business_id
                    )
                )

                updated=cur.rowcount

                conn.commit()

                if not updated:

                    flash(
                        "Reward not found.",
                        "error"
                    )

                else:

                    flash(
                        "Reward updated successfully! 🎉",
                        "success"
                    )

                return redirect(
                    url_for("owner_rewards")
                )


            cur.execute(
                """
                SELECT
                    id,
                    reward_name,
                    description,
                    reward_value,
                    required_stamps,
                    validity_days,
                    status,
                    created_at
                FROM rewards
                WHERE id=%s
                AND business_id=%s
                """,
                (
                    reward_id,
                    business_id
                )
            )

            reward=cur.fetchone()

            if not reward:

                flash(
                    "Reward not found.",
                    "error"
                )

                return redirect(
                    url_for("owner_rewards")
                )


            cur.execute(
                """
                SELECT
                    business_name,
                    city,
                    business_code
                FROM businesses
                WHERE id=%s
                """,
                (business_id,)
            )

            business=cur.fetchone()

        return render_template(
            "owner/loyalty/edit_reward.html",
            reward=reward,
            business_name=business[0] if business else "Business",
            city=business[1] if business else "",
            business_code=business[2] if business else None,
            header_section="LOYALTY",
            header_title="Edit Reward"
        )

    except Exception as error:

        conn.rollback()

        app.logger.exception(
            "Edit reward error: %s",
            error
        )

        flash(
            "Unable to update reward.",
            "error"
        )

        return redirect(
            url_for("owner_rewards")
        )

    finally:

        conn.close()

@app.route("/owner/reminders")
@owner_required
def owner_reminders():
    business_id=session.get("business_id")
    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))
    conn=get_db_connection()
    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_dashboard"))
    cur=conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*),
                   COUNT(*) FILTER(WHERE status='pending'),
                   COUNT(*) FILTER(WHERE status='sent'),
                   COUNT(*) FILTER(WHERE status='cancelled')
            FROM reminders
            WHERE business_id=%s
        """,(business_id,))
        row=cur.fetchone()
        stats={"total":row[0] or 0,"pending":row[1] or 0,"sent":row[2] or 0,"cancelled":row[3] or 0}

        cur.execute("""
            SELECT id,full_name,phone
            FROM customers
            WHERE business_id=%s AND is_active=TRUE
            ORDER BY full_name
        """,(business_id,))
        customers=cur.fetchall()

        cur.execute("""
            SELECT r.id,r.customer_id,c.full_name,c.phone,
                   r.reminder_type,r.subject,r.message,
                   r.scheduled_at,r.status,r.sent_at
            FROM reminders r
            JOIN customers c ON c.id=r.customer_id
            WHERE r.business_id=%s
            ORDER BY CASE WHEN r.status='pending' THEN 0 ELSE 1 END,
                     r.scheduled_at DESC
        """,(business_id,))
        reminders=cur.fetchall()

        return render_template("owner/reminders/reminders.html",stats=stats,customers=customers,reminders=reminders)
    except Exception as e:
        conn.rollback()
        print("REMINDER LOAD ERROR:",repr(e))
        flash(f"Unable to load reminders: {e}","error")
        return redirect(url_for("owner_dashboard"))
    finally:
        cur.close()
        conn.close()


@app.route("/owner/reminders/create",methods=["POST"])
@owner_required
def create_reminder():
    business_id=session.get("business_id")
    customer_id=request.form.get("customer_id","").strip()
    reminder_type=request.form.get("reminder_type","custom").strip().lower()
    title=request.form.get("title","").strip()
    message=request.form.get("message","").strip()
    scheduled_at=request.form.get("scheduled_at","").strip()

    if reminder_type not in {"revisit","offer","reward","followup","custom"}:
        reminder_type="custom"
    if not customer_id or not title or not message or not scheduled_at:
        flash("Please fill all reminder fields.","error")
        return redirect(url_for("owner_reminders"))

    conn=get_db_connection()
    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_reminders"))
    cur=conn.cursor()
    try:
        cur.execute("""
            SELECT id FROM customers
            WHERE id=%s AND business_id=%s AND is_active=TRUE
        """,(customer_id,business_id))
        if not cur.fetchone():
            flash("Customer not found.","error")
            return redirect(url_for("owner_reminders"))

        cur.execute("""
            INSERT INTO reminders(
                business_id,customer_id,reminder_type,
                subject,message,scheduled_at
            )
            VALUES(%s,%s,%s,%s,%s,%s)
        """,(business_id,customer_id,reminder_type,title,message,scheduled_at))
        conn.commit()
        flash("Reminder scheduled successfully!","success")
    except Exception as e:
        conn.rollback()
        print("CREATE REMINDER ERROR:",repr(e))
        flash(f"Unable to create reminder: {e}","error")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("owner_reminders"))


@app.route("/owner/reminders/<reminder_id>/status",methods=["POST"])
@owner_required
def update_reminder_status(reminder_id):
    business_id=session.get("business_id")
    new_status=request.form.get("status","").strip().lower()

    if new_status not in {"pending","sent","cancelled"}:
        flash("Invalid reminder status.","error")
        return redirect(url_for("owner_reminders"))

    conn=get_db_connection()
    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_reminders"))
    cur=conn.cursor()
    try:
        if new_status=="sent":
            cur.execute("""
                UPDATE reminders
                SET status='sent',
                    sent_at=COALESCE(sent_at,CURRENT_TIMESTAMP),
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND business_id=%s AND status='pending'
            """,(reminder_id,business_id))
        elif new_status=="cancelled":
            cur.execute("""
                UPDATE reminders
                SET status='cancelled',
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND business_id=%s AND status='pending'
            """,(reminder_id,business_id))
        else:
            cur.execute("""
                UPDATE reminders
                SET status='pending',
                    sent_at=NULL,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=%s AND business_id=%s
            """,(reminder_id,business_id))

        if cur.rowcount==0:
            flash("Reminder not found or cannot be updated.","error")
        else:
            flash("Reminder status updated successfully.","success")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("UPDATE REMINDER ERROR:",repr(e))
        flash(f"Unable to update reminder: {e}","error")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("owner_reminders"))


@app.route("/owner/reminders/<reminder_id>/delete",methods=["POST"])
@owner_required
def delete_reminder(reminder_id):
    business_id=session.get("business_id")
    conn=get_db_connection()
    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_reminders"))
    cur=conn.cursor()
    try:
        cur.execute("""
            DELETE FROM reminders
            WHERE id=%s AND business_id=%s
        """,(reminder_id,business_id))
        flash("Reminder deleted successfully." if cur.rowcount else "Reminder not found.",
              "success" if cur.rowcount else "error")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("DELETE REMINDER ERROR:",repr(e))
        flash(f"Unable to delete reminder: {e}","error")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("owner_reminders"))


@app.route("/owner/reminders/settings",methods=["GET","POST"])
@owner_required
def reminder_settings():
    business_id=session.get("business_id")
    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))

    conn=get_db_connection()
    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_dashboard"))
    cur=conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reminder_settings(
                id BIGSERIAL PRIMARY KEY,
                business_id UUID NOT NULL UNIQUE
                    REFERENCES businesses(id) ON DELETE CASCADE,
                is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                default_days_after_visit INTEGER NOT NULL DEFAULT 7,
                daily_limit INTEGER NOT NULL DEFAULT 100,
                default_message TEXT NOT NULL
                    DEFAULT 'We miss you! Visit us again soon.',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            INSERT INTO reminder_settings(business_id)
            VALUES(%s)
            ON CONFLICT(business_id) DO NOTHING
        """,(business_id,))

        if request.method=="POST":
            is_enabled=request.form.get("is_enabled")=="1"
            try:
                days=max(1,min(365,int(request.form.get("default_days_after_visit","7"))))
            except ValueError:
                days=7
            try:
                daily_limit=max(1,min(10000,int(request.form.get("daily_limit","100"))))
            except ValueError:
                daily_limit=100

            message=request.form.get("default_message","").strip()
            if not message:
                message="We miss you! Visit us again soon."

            cur.execute("""
                UPDATE reminder_settings
                SET is_enabled=%s,
                    default_days_after_visit=%s,
                    daily_limit=%s,
                    default_message=%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE business_id=%s
            """,(is_enabled,days,daily_limit,message,business_id))
            conn.commit()
            flash("Reminder settings updated successfully!","success")
            return redirect(url_for("reminder_settings"))

        cur.execute("""
            SELECT is_enabled,default_days_after_visit,
                   daily_limit,default_message
            FROM reminder_settings
            WHERE business_id=%s
        """,(business_id,))
        row=cur.fetchone()

        settings={
            "is_enabled":row[0],
            "default_days_after_visit":row[1],
            "daily_limit":row[2],
            "default_message":row[3]
        }

        return render_template(
            "owner/reminders/reminder_settings.html",
            settings=settings
        )

    except Exception as e:
        conn.rollback()
        print("REMINDER SETTINGS ERROR:",repr(e))
        flash(f"Unable to load reminder settings: {e}","error")
        return redirect(url_for("owner_reminders"))
    finally:
        cur.close()
        conn.close()


@app.route("/owner/rewards/claims")
@owner_required
def owner_reward_claims():
    business_id=session.get("business_id")
    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))
    conn=get_db_connection()
    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_dashboard"))
    cur=conn.cursor()
    try:
        cur.execute("""
            SELECT COUNT(*),
                   COUNT(*) FILTER(WHERE rc.status='claimed'),
                   COUNT(*) FILTER(WHERE rc.status='redeemed'),
                   COUNT(*) FILTER(WHERE rc.status='expired'),
                   COUNT(*) FILTER(WHERE rc.status='cancelled')
            FROM reward_claims rc
            WHERE rc.business_id=%s
        """,(business_id,))
        row=cur.fetchone()
        stats={
            "total":row[0] or 0,
            "claimed":row[1] or 0,
            "redeemed":row[2] or 0,
            "expired":row[3] or 0,
            "cancelled":row[4] or 0
        }

        cur.execute("""
            SELECT
                rc.id,
                rc.claim_code,
                rc.status,
                rc.claimed_at,
                rc.redeemed_at,
                rc.expires_at,
                r.id,
                r.reward_name,
                r.reward_value,
                r.required_stamps,
                c.id,
                c.full_name,
                c.phone,
                c.email
            FROM reward_claims rc
            JOIN rewards r ON r.id=rc.reward_id
            JOIN customers c ON c.id=rc.customer_id
            WHERE rc.business_id=%s
            ORDER BY rc.created_at DESC
        """,(business_id,))
        claims=cur.fetchall()

        return render_template(
            "owner/rewards/reward_claims.html",
            stats=stats,
            claims=claims
        )
    except Exception as e:
        conn.rollback()
        print("REWARD CLAIMS ERROR:",repr(e))
        flash(f"Unable to load reward claims: {e}","error")
        return redirect(url_for("owner_dashboard"))
    finally:
        cur.close()
        conn.close()


@app.route("/owner/rewards/claims/<claim_id>")
@owner_required
def reward_claim_details(claim_id):
    business_id=session.get("business_id")
    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))
    conn=get_db_connection()
    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_dashboard"))
    cur=conn.cursor()
    try:
        cur.execute("""
            SELECT
                rc.id,
                rc.claim_code,
                rc.status,
                rc.claimed_at,
                rc.redeemed_at,
                rc.expires_at,
                rc.created_at,
                r.id,
                r.reward_name,
                r.description,
                r.reward_value,
                r.required_stamps,
                r.validity_days,
                c.id,
                c.full_name,
                c.phone,
                c.email,
                c.total_visits,
                c.total_orders,
                c.total_spent
            FROM reward_claims rc
            JOIN rewards r ON r.id=rc.reward_id
            JOIN customers c ON c.id=rc.customer_id
            WHERE rc.id=%s AND rc.business_id=%s
            LIMIT 1
        """,(claim_id,business_id))
        claim=cur.fetchone()
        if not claim:
            flash("Reward claim not found.","error")
            return redirect(url_for("owner_reward_claims"))

        return render_template(
            "owner/rewards/reward_details.html",
            claim=claim
        )
    except Exception as e:
        conn.rollback()
        print("REWARD CLAIM DETAILS ERROR:",repr(e))
        flash(f"Unable to load reward details: {e}","error")
        return redirect(url_for("owner_reward_claims"))
    finally:
        cur.close()
        conn.close()


@app.route("/owner/rewards/claims/<claim_id>/status",methods=["POST"])
@owner_required
def update_reward_claim_status(claim_id):
    business_id=session.get("business_id")
    new_status=request.form.get("status","").strip().lower()
    allowed={"claimed","redeemed","expired","cancelled"}
    if new_status not in allowed:
        flash("Invalid reward claim status.","error")
        return redirect(url_for("owner_reward_claims"))

    conn=get_db_connection()
    if not conn:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_reward_claims"))
    cur=conn.cursor()
    try:
        if new_status=="redeemed":
            cur.execute("""
                UPDATE reward_claims
                SET status='redeemed',
                    redeemed_at=COALESCE(redeemed_at,CURRENT_TIMESTAMP)
                WHERE id=%s AND business_id=%s
            """,(claim_id,business_id))
        elif new_status=="claimed":
            cur.execute("""
                UPDATE reward_claims
                SET status='claimed',
                    redeemed_at=NULL
                WHERE id=%s AND business_id=%s
            """,(claim_id,business_id))
        else:
            cur.execute("""
                UPDATE reward_claims
                SET status=%s
                WHERE id=%s AND business_id=%s
            """,(new_status,claim_id,business_id))

        if cur.rowcount==0:
            flash("Reward claim not found.","error")
        else:
            flash("Reward claim status updated successfully.","success")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print("UPDATE REWARD CLAIM ERROR:",repr(e))
        flash(f"Unable to update reward claim: {e}","error")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("reward_claim_details",claim_id=claim_id))

@app.route("/analytics")
@owner_required
def analytics():

    business_id=session.get("business_id")

    if not business_id:
        flash("Business not found.","error")
        return redirect(url_for("owner_dashboard"))

    connection=get_db_connection()

    if not connection:
        flash("Database connection failed.","error")
        return redirect(url_for("owner_dashboard"))

    try:

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT business_name,city,business_code
                FROM businesses
                WHERE id=%s
            """,(business_id,))

            business=cursor.fetchone()

            if not business:
                flash("Business not found.","error")
                return redirect(url_for("owner_dashboard"))

            business_name,city,business_code=business

            cursor.execute("""
                SELECT COUNT(*)
                FROM customers
                WHERE business_id=%s
            """,(business_id,))
            total_customers=cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*)
                FROM customers
                WHERE business_id=%s
                AND is_active=TRUE
            """,(business_id,))
            active_customers=cursor.fetchone()[0] or 0

            inactive_customers=total_customers-active_customers

            cursor.execute("""
                SELECT COUNT(*)
                FROM customers
                WHERE business_id=%s
                AND total_visits>=2
            """,(business_id,))
            returning_customers=cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*)
                FROM orders
                WHERE business_id=%s
            """,(business_id,))
            total_orders=cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*)
                FROM orders
                WHERE business_id=%s
                AND status='delivered'
            """,(business_id,))
            delivered_orders=cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COALESCE(SUM(total_amount),0)
                FROM orders
                WHERE business_id=%s
                AND status='delivered'
            """,(business_id,))
            total_revenue=float(cursor.fetchone()[0] or 0)

            average_order_value=(
                total_revenue/delivered_orders
                if delivered_orders else 0
            )

            cursor.execute("""
                SELECT COUNT(*)
                FROM customer_visits
                WHERE business_id=%s
            """,(business_id,))
            total_visits=cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COALESCE(SUM(stamp_count),0)
                FROM loyalty_stamps
                WHERE business_id=%s
            """,(business_id,))
            total_stamps=cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*)
                FROM reward_claims
                WHERE business_id=%s
                AND status='claimed'
            """,(business_id,))
            rewards_claimed=cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*)
                FROM customers c
                WHERE c.business_id=%s
                AND c.is_active=TRUE
                AND (
                    SELECT COALESCE(SUM(ls.stamp_count),0)
                    FROM loyalty_stamps ls
                    WHERE ls.customer_id=c.id
                    AND ls.business_id=%s
                ) >= COALESCE((
                    SELECT reward_stamps_required
                    FROM loyalty_settings
                    WHERE business_id=%s
                    LIMIT 1
                ),999999)
            """,(business_id,business_id,business_id))

            eligible_customers=cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT
                    d.day::date,
                    COUNT(o.id),
                    COALESCE(SUM(
                        CASE
                            WHEN o.status='delivered'
                            THEN o.total_amount
                            ELSE 0
                        END
                    ),0)
                FROM generate_series(
                    CURRENT_DATE-INTERVAL '6 days',
                    CURRENT_DATE,
                    INTERVAL '1 day'
                ) d(day)
                LEFT JOIN orders o
                    ON o.business_id=%s
                    AND o.created_at::date=d.day::date
                GROUP BY d.day
                ORDER BY d.day
            """,(business_id,))

            rows=cursor.fetchall()

            max_revenue=max(
                [float(row[2] or 0) for row in rows],
                default=0
            )

            daily_stats=[
                (
                    row[0],
                    row[1],
                    float(row[2] or 0),
                    round(
                        (float(row[2] or 0)/max_revenue)*100,
                        2
                    ) if max_revenue else 0
                )
                for row in rows
            ]

            cursor.execute("""
                SELECT
                    oi.item_name,
                    SUM(oi.quantity),
                    SUM(oi.total_price)
                FROM order_items oi
                JOIN orders o
                    ON o.id=oi.order_id
                WHERE oi.business_id=%s
                AND o.status='delivered'
                GROUP BY oi.item_name
                ORDER BY SUM(oi.quantity) DESC
                LIMIT 5
            """,(business_id,))

            top_items=cursor.fetchall()

        return render_template(
            "owner/analytics/analytics.html",
            business_name=business_name,
            city=city,
            business_code=business_code,
            total_customers=total_customers,
            active_customers=active_customers,
            inactive_customers=inactive_customers,
            returning_customers=returning_customers,
            total_orders=total_orders,
            delivered_orders=delivered_orders,
            total_revenue=total_revenue,
            average_order_value=average_order_value,
            total_visits=total_visits,
            total_stamps=total_stamps,
            rewards_claimed=rewards_claimed,
            eligible_customers=eligible_customers,
            daily_stats=daily_stats,
            top_items=top_items
        )

    except Exception as e:

        connection.rollback()
        print("Analytics error:",e)

        flash("Unable to load analytics.","error")

        return redirect(url_for("owner_dashboard"))

    finally:
        connection.close()


@app.route("/owner/qr")
@owner_required
def qr_code():

    business_id = session.get("business_id")

    if not business_id:
        flash("Business not found.", "error")
        return redirect(url_for("owner_dashboard"))

    conn = get_db_connection()

    if not conn:
        flash("Database connection failed.", "error")
        return redirect(url_for("owner_dashboard"))

    try:

        with conn.cursor() as cur:

            # Get business details
            cur.execute("""
                SELECT
                    id,
                    business_name,
                    business_code,
                    city,
                    state
                FROM businesses
                WHERE id = %s
                LIMIT 1
            """, (business_id,))

            business = cur.fetchone()

            if not business:
                flash("Business not found.", "error")
                return redirect(url_for("owner_dashboard"))

            business_id_db = business[0]
            business_name = business[1]
            business_code = business[2]
            city = business[3]
            state = business[4]

            # Keep owner session updated
            session["business_id"] = str(business_id_db)
            session["business_name"] = business_name

            # -------------------------------------------------
            # GET EXISTING QR CODE
            # -------------------------------------------------

            cur.execute("""
                SELECT
                    id,
                    qr_token,
                    qr_url,
                    is_active
                FROM business_qr_codes
                WHERE business_id = %s
                LIMIT 1
            """, (business_id_db,))

            qr_record = cur.fetchone()

            # -------------------------------------------------
            # CREATE QR RECORD IF NOT EXISTS
            # -------------------------------------------------

            if not qr_record:

                import secrets

                qr_token = secrets.token_urlsafe(9).replace("-", "").replace("_", "").upper()

                customer_url = (
                    request.url_root.rstrip("/")
                    + "/business/"
                    + qr_token
                )

                cur.execute("""
                    INSERT INTO business_qr_codes
                    (
                        business_id,
                        qr_token,
                        qr_url,
                        is_active
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        TRUE
                    )
                    RETURNING id, qr_token, qr_url, is_active
                """, (
                    business_id_db,
                    qr_token,
                    customer_url
                ))

                qr_record = cur.fetchone()

                conn.commit()

            else:

                qr_id = qr_record[0]
                qr_token = qr_record[1]
                old_qr_url = qr_record[2]
                qr_is_active = qr_record[3]

                # -------------------------------------------------
                # ALWAYS KEEP QR URL CORRECT
                # -------------------------------------------------

                customer_url = (
                    request.url_root.rstrip("/")
                    + "/business/"
                    + str(qr_token)
                )

                # Update old /customer URL if necessary
                if old_qr_url != customer_url:

                    cur.execute("""
                        UPDATE business_qr_codes
                        SET qr_url = %s
                        WHERE id = %s
                    """, (
                        customer_url,
                        qr_id
                    ))

                    conn.commit()

                # If QR was inactive, keep it inactive.
                # It can be activated separately from DB/settings.

            # -------------------------------------------------
            # GENERATE QR IMAGE
            # -------------------------------------------------

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=12,
                border=4
            )

            qr.add_data(customer_url)
            qr.make(fit=True)

            qr_image = qr.make_image(
                fill_color="black",
                back_color="white"
            )

            # -------------------------------------------------
            # CONVERT QR IMAGE TO BASE64
            # -------------------------------------------------

            buffer = io.BytesIO()

            qr_image.save(
                buffer,
                format="PNG"
            )

            buffer.seek(0)

            import base64

            qr_base64 = base64.b64encode(
                buffer.getvalue()
            ).decode("utf-8")

            qr_code_data = (
                "data:image/png;base64,"
                + qr_base64
            )

            # -------------------------------------------------
            # RENDER QR PAGE
            # -------------------------------------------------

            return render_template(
                "owner/qr/qr_code.html",
                business_name=business_name,
                business_code=business_code,
                city=city,
                state=state,
                customer_url=customer_url,
                qr_token=qr_token,
                qr_code=qr_code_data,
                header_section="BUSINESS",
                header_title="QR Code"
            )

    except Exception as error:

        if conn:
            conn.rollback()

        print(
            "QR CODE ERROR:",
            repr(error)
        )

        app.logger.exception(
            "QR Code generation failed"
        )

        flash(
            f"Unable to load QR Code: {error}",
            "error"
        )

        return redirect(
            url_for("owner_dashboard")
        )

    finally:

        if conn:
            conn.close()

@app.route("/business/<qr_token>")
def business_page(qr_token):

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    q.qr_token,
                    q.business_id,
                    q.qr_url,
                    q.is_active,

                    b.business_name,
                    b.logo_url,
                    b.description,
                    b.phone,
                    b.email,
                    b.address,
                    b.city,
                    b.state,
                    b.country,
                    b.pincode,
                    b.instagram_url,
                    b.google_review_url,
                    b.whatsapp_number,
                    b.status

                FROM business_qr_codes q

                INNER JOIN businesses b
                    ON b.id = q.business_id

                WHERE q.qr_token = %s
                  AND q.is_active = TRUE
                  AND b.status = 'active'

                LIMIT 1
            """, (qr_token,))

            row = cursor.fetchone()

            if not row:
                return "QR code is invalid or inactive.", 404

            # -------------------------------------------------
            # CONVERT TUPLE TO DICTIONARY
            # -------------------------------------------------

            business = {
                "qr_token": row[0],
                "business_id": row[1],
                "qr_url": row[2],
                "is_active": row[3],

                "business_name": row[4],
                "logo_url": row[5],
                "description": row[6],
                "phone": row[7],
                "email": row[8],
                "address": row[9],
                "city": row[10],
                "state": row[11],
                "country": row[12],
                "pincode": row[13],

                "instagram_url": row[14],
                "google_review_url": row[15],
                "whatsapp_number": row[16],

                "status": row[17]
            }

        return render_template(
            "customer/business.html",
            business=business,
            qr_token=qr_token
        )

    except Exception as error:

        print(
            "BUSINESS PAGE ERROR:",
            repr(error)
        )

        app.logger.exception(
            "Business page failed"
        )

        return "Unable to load business page.", 500

    finally:

        if connection:
            connection.close()


@app.route("/owner/logout")
def owner_logout():
    session.clear()
    flash("You have been logged out.","success")
    return redirect(url_for("owner_login"))















def customer_login_required(view_function):

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):

        customer_id = session.get("customer_id")
        business_id = session.get("customer_business_id")
        qr_token = session.get("customer_qr_token")

        # -----------------------------------------
        # SESSION CHECK
        # -----------------------------------------
        if not customer_id or not business_id:

            return redirect(
                url_for(
                    "customer_login",
                    qr_token=qr_token or kwargs.get("qr_token", "")
                )
            )

        connection = None

        try:

            connection = get_db_connection()

            if not connection:

                session.clear()

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=qr_token or kwargs.get("qr_token", "")
                    )
                )

            with connection.cursor() as cursor:

                cursor.execute("""
                    SELECT
                        c.id,
                        c.business_id,
                        c.full_name,
                        c.email,
                        c.phone,
                        c.is_active,
                        b.business_name,
                        b.status
                    FROM customers c
                    INNER JOIN businesses b
                        ON b.id = c.business_id
                    WHERE c.id = %s
                      AND c.business_id = %s
                    LIMIT 1
                """, (
                    customer_id,
                    business_id
                ))

                customer = cursor.fetchone()

            # -----------------------------------------
            # CUSTOMER NOT FOUND
            # -----------------------------------------
            if not customer:

                session.clear()

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=qr_token or kwargs.get("qr_token", "")
                    )
                )

            # tuple:
            # 0 id
            # 1 business_id
            # 2 full_name
            # 3 email
            # 4 phone
            # 5 customer is_active
            # 6 business_name
            # 7 business status

            customer_active = customer[5]
            business_status = customer[7]

            # -----------------------------------------
            # CUSTOMER INACTIVE
            # -----------------------------------------
            if not customer_active:

                session.clear()

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=qr_token or kwargs.get("qr_token", "")
                    )
                )

            # -----------------------------------------
            # BUSINESS INACTIVE
            # -----------------------------------------
            if business_status != "active":

                session.clear()

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=qr_token or kwargs.get("qr_token", "")
                    )
                )

            return view_function(*args, **kwargs)

        except Exception as error:

            print("\n===================================")
            print("CUSTOMER AUTH ERROR")
            print("===================================")
            print(error)
            print("===================================\n")

            app.logger.exception(
                "Customer authentication failed"
            )

            session.clear()

            return redirect(
                url_for(
                    "customer_login",
                    qr_token=qr_token or kwargs.get("qr_token", "")
                )
            )

        finally:

            if connection:
                connection.close()

    return wrapped_view


@app.route("/customer/profile", methods=["GET"])
@customer_login_required
def customer_profile():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")
    qr_token = session.get("customer_qr_token", "")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            flash("Database connection failed.", "danger")
            return redirect(url_for("customer_dashboard"))

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    c.id,
                    c.business_id,
                    c.full_name,
                    c.email,
                    c.phone,
                    c.total_visits,
                    c.total_orders,
                    c.total_spent,
                    c.last_visit_at,
                    c.last_order_at,
                    c.is_active,

                    b.id,
                    b.business_name,
                    b.logo_url,
                    b.description,
                    b.phone,
                    b.email,
                    b.address,
                    b.city,
                    b.state,
                    b.pincode,
                    b.instagram_url,
                    b.google_review_url,
                    b.whatsapp_number,
                    b.status

                FROM customers c

                INNER JOIN businesses b
                    ON b.id = c.business_id

                WHERE c.id = %s
                  AND c.business_id = %s
                  AND c.is_active = TRUE
                  AND b.status = 'active'

                LIMIT 1
            """, (
                customer_id,
                business_id
            ))

            row = cursor.fetchone()

            if not row:
                flash("Customer profile not found.", "danger")
                return redirect(url_for("customer_dashboard"))

            customer = {
                "id": row[0],
                "business_id": row[1],
                "full_name": row[2],
                "email": row[3],
                "phone": row[4],
                "total_visits": row[5] or 0,
                "total_orders": row[6] or 0,
                "total_spent": row[7] or 0,
                "last_visit_at": row[8],
                "last_order_at": row[9],
                "is_active": row[10]
            }

            business = {
                "id": row[11],
                "business_name": row[12],
                "logo_url": row[13],
                "description": row[14],
                "phone": row[15],
                "email": row[16],
                "address": row[17],
                "city": row[18],
                "state": row[19],
                "pincode": row[20],
                "instagram_url": row[21],
                "google_review_url": row[22],
                "whatsapp_number": row[23],
                "status": row[24]
            }

        return render_template(
            "customer/profile.html",
            customer=customer,
            business=business,
            qr_token=qr_token
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER PROFILE ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer profile failed"
        )

        flash(
            "Unable to load profile.",
            "danger"
        )

        return redirect(
            url_for("customer_dashboard")
        )

    finally:

        if connection:
            connection.close()


@app.route("/customer/login/<qr_token>", methods=["GET", "POST"])
def customer_login(qr_token):

    qr_token = clean_text(qr_token, 255)

    if not qr_token:
        abort(404)

    connection = None

    try:

        connection = get_db_connection()

        if not connection:

            flash(
                "Database connection failed.",
                "danger"
            )

            return render_template(
                "auth/customer_login.html",
                qr_token=qr_token
            )

        with connection.cursor() as cursor:

            # =========================================
            # FIND BUSINESS USING QR
            # =========================================

            cursor.execute("""
                SELECT
                    q.qr_token,
                    q.business_id,
                    b.business_name,
                    b.status,
                    q.is_active
                FROM business_qr_codes q
                INNER JOIN businesses b
                    ON b.id = q.business_id
                WHERE q.qr_token = %s
                  AND q.is_active = TRUE
                  AND b.status = 'active'
                LIMIT 1
            """, (
                qr_token,
            ))

            business_row = cursor.fetchone()

            # =========================================
            # QR NOT FOUND
            # =========================================

            if not business_row:

                flash(
                    "This QR code is invalid or inactive.",
                    "danger"
                )

                return render_template(
                    "auth/customer_login.html",
                    qr_token=qr_token
                ), 404

            # =========================================
            # BUSINESS DATA
            # =========================================

            business_id = business_row[1]

            business = {
                "qr_token": business_row[0],
                "business_id": business_row[1],
                "business_name": business_row[2],
                "status": business_row[3],
                "is_active": business_row[4]
            }

            # =========================================
            # POST LOGIN
            # =========================================

            if request.method == "POST":

                phone = normalize_phone(
                    request.form.get("phone", "")
                )

                print("\n===================================")
                print("CUSTOMER LOGIN")
                print("===================================")
                print("QR TOKEN:", qr_token)
                print("BUSINESS ID:", business_id)
                print("PHONE:", phone)

                # =====================================
                # PHONE VALIDATION
                # =====================================

                if not phone:

                    flash(
                        "Please enter a valid mobile number.",
                        "danger"
                    )

                    return render_template(
                        "auth/customer_login.html",
                        qr_token=qr_token,
                        business=business
                    )

                # =====================================
                # FIND CUSTOMER
                # =====================================

                cursor.execute("""
                    SELECT
                        id,
                        business_id,
                        full_name,
                        email,
                        phone,
                        is_active
                    FROM customers
                    WHERE business_id = %s
                      AND phone = %s
                    LIMIT 1
                """, (
                    business_id,
                    phone
                ))

                customer = cursor.fetchone()

                print("CUSTOMER RESULT:", customer)

                # =====================================
                # CUSTOMER NOT FOUND
                # =====================================

                if not customer:

                    print("CUSTOMER NOT FOUND")

                    flash(
                        "Account not found. Please create your account first.",
                        "warning"
                    )

                    return redirect(
                        url_for(
                            "customer_register",
                            qr_token=qr_token
                        )
                    )

                # =====================================
                # CUSTOMER INACTIVE
                # =====================================

                if not customer[5]:

                    flash(
                        "Your customer account is inactive.",
                        "danger"
                    )

                    return render_template(
                        "auth/customer_login.html",
                        qr_token=qr_token,
                        business=business
                    )

                # =====================================
                # CLEAR OLD SESSION
                # =====================================

                session.clear()

                # =====================================
                # CUSTOMER SESSION
                # =====================================

                session["customer_id"] = str(
                    customer[0]
                )

                session["customer_business_id"] = str(
                    customer[1]
                )

                session["customer_qr_token"] = qr_token

                session["customer_name"] = customer[2]

                session["customer_logged_in"] = True

                session.permanent = True

                print("CUSTOMER LOGIN SUCCESS")
                print("CUSTOMER ID:", customer[0])
                print("BUSINESS ID:", customer[1])

                print("===================================\n")

                # =====================================
                # GO TO CUSTOMER DASHBOARD
                # =====================================

                return redirect(
                    url_for(
                        "customer_dashboard"
                    )
                )

        # =========================================
        # GET LOGIN PAGE
        # =========================================

        return render_template(
            "auth/customer_login.html",
            qr_token=qr_token,
            business=business
        )

    except Exception as error:

        print("\n===================================")
        print("CUSTOMER LOGIN ERROR")
        print("===================================")
        print(error)
        print("===================================\n")

        app.logger.exception(
            "Customer login failed"
        )

        if connection:

            try:
                connection.rollback()
            except Exception:
                pass

        flash(
            "Unable to login right now. Please try again.",
            "danger"
        )

        return render_template(
            "auth/customer_login.html",
            qr_token=qr_token,
            business=locals().get("business")
        )

    finally:

        if connection:
            connection.close()

@app.route("/customer/register/<qr_token>", methods=["GET", "POST"])
def customer_register(qr_token):

    qr_token = clean_text(qr_token, 255)

    if not qr_token:
        abort(404)

    connection = None

    try:
        connection = get_db_connection()

        if not connection:
            flash("Database connection failed. Please try again.", "danger")
            return render_template(
                "auth/customer_register.html",
                qr_token=qr_token
            )

        with connection.cursor() as cursor:

            # GET BUSINESS FROM QR
            cursor.execute("""
                SELECT
                    q.qr_token,
                    q.business_id,
                    b.business_name,
                    b.status,
                    q.is_active
                FROM business_qr_codes q
                INNER JOIN businesses b
                    ON b.id = q.business_id
                WHERE q.qr_token = %s
                  AND q.is_active = TRUE
                  AND b.status = 'active'
                LIMIT 1
            """, (qr_token,))

            business_row = cursor.fetchone()

            if not business_row:
                flash(
                    "This QR code is invalid or inactive.",
                    "danger"
                )
                return render_template(
                    "auth/customer_register.html",
                    qr_token=qr_token
                )

            # psycopg returns tuple
            business_id = business_row[1]
            business_name = business_row[2]

            business = {
                "qr_token": business_row[0],
                "business_id": business_row[1],
                "business_name": business_row[2],
                "status": business_row[3],
                "is_active": business_row[4]
            }

            # =========================
            # POST
            # =========================
            if request.method == "POST":

                full_name = clean_text(
                    request.form.get("full_name"),
                    100
                )

                phone = normalize_phone(
                    request.form.get("phone")
                )

                email = normalize_email(
                    request.form.get("email")
                )

                # NAME VALIDATION
                if not full_name:
                    flash(
                        "Please enter your full name.",
                        "danger"
                    )
                    return render_template(
                        "auth/customer_register.html",
                        qr_token=qr_token,
                        business=business
                    )

                # PHONE VALIDATION
                if not phone:
                    flash(
                        "Please enter a valid mobile number.",
                        "danger"
                    )
                    return render_template(
                        "auth/customer_register.html",
                        qr_token=qr_token,
                        business=business
                    )

                # =========================
                # CHECK EXISTING CUSTOMER
                # =========================
                cursor.execute("""
                    SELECT
                        id,
                        business_id,
                        full_name,
                        email,
                        phone,
                        is_active
                    FROM customers
                    WHERE business_id = %s
                      AND phone = %s
                    LIMIT 1
                """, (
                    business_id,
                    phone
                ))

                existing_customer = cursor.fetchone()

                if existing_customer:

                    if existing_customer[5]:

                        flash(
                            "You are already registered. Please login.",
                            "warning"
                        )

                        return redirect(
                            url_for(
                                "customer_login",
                                qr_token=qr_token
                            )
                        )

                    else:

                        flash(
                            "Your customer account is inactive.",
                            "danger"
                        )

                        return render_template(
                            "auth/customer_register.html",
                            qr_token=qr_token,
                            business=business
                        )

                # =========================
                # CREATE CUSTOMER
                # =========================
                cursor.execute("""
                    INSERT INTO customers (
                        business_id,
                        full_name,
                        email,
                        phone,
                        is_active,
                        email_verified,
                        phone_verified,
                        total_visits,
                        total_orders,
                        total_spent,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        TRUE,
                        FALSE,
                        FALSE,
                        0,
                        0,
                        0,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    RETURNING
                        id,
                        business_id,
                        full_name
                """, (
                    business_id,
                    full_name,
                    email if email else None,
                    phone
                ))

                customer = cursor.fetchone()

                if not customer:
                    raise Exception(
                        "Customer insert failed."
                    )

                customer_id = customer[0]
                customer_business_id = customer[1]
                customer_name = customer[2]

                # =========================
                # RECORD VISIT
                # =========================
                cursor.execute("""
                    INSERT INTO customer_visits (
                        business_id,
                        customer_id,
                        visit_at,
                        source
                    )
                    VALUES (
                        %s,
                        %s,
                        CURRENT_TIMESTAMP,
                        'qr'
                    )
                """, (
                    business_id,
                    customer_id
                ))

                # =========================
                # UPDATE CUSTOMER VISIT
                # =========================
                cursor.execute("""
                    UPDATE customers
                    SET
                        total_visits = total_visits + 1,
                        last_visit_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                      AND business_id = %s
                """, (
                    customer_id,
                    business_id
                ))

                # =========================
                # COMMIT
                # =========================
                connection.commit()

                # =========================
                # CUSTOMER SESSION
                # =========================
                session.clear()

                session["customer_id"] = str(customer[0])
                session["customer_business_id"] = str(customer[1])
                session["customer_qr_token"] = qr_token
                session["customer_name"] = customer[2]
                session["customer_logged_in"] = True
                session.permanent = True

                session["customer_id"] = str(
                    customer_id
                )

                session["customer_business_id"] = str(
                    customer_business_id
                )

                session["customer_qr_token"] = qr_token

                session["customer_name"] = customer_name

                session.permanent = True

                flash(
                    f"Welcome to {business_name}! 🎉",
                    "success"
                )

                return redirect(
                    url_for("customer_dashboard")
                )

            # =========================
            # GET
            # =========================
            return render_template(
                "auth/customer_register.html",
                qr_token=qr_token,
                business=business
            )

    except Exception as error:

        if connection:
            try:
                connection.rollback()
            except Exception:
                pass

        print("\n====================================")
        print("CUSTOMER REGISTRATION ERROR")
        print("====================================")
        print(error)
        print("====================================\n")

        app.logger.exception(
            "Customer registration failed"
        )

        flash(
            "Unable to create account right now. Please try again.",
            "danger"
        )

        return render_template(
            "auth/customer_register.html",
            qr_token=qr_token
        )

    finally:

        if connection:
            connection.close()


@app.route("/customer/dashboard", methods=["GET"])
@customer_login_required
def customer_dashboard():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            flash(
                "Database connection failed.",
                "danger"
            )
            return redirect(
                url_for(
                    "customer_login",
                    qr_token=session.get("customer_qr_token", "")
                )
            )

        with connection.cursor() as cursor:

            # =========================================
            # CUSTOMER + BUSINESS
            # =========================================
            cursor.execute("""
                SELECT
                    c.id,
                    c.business_id,
                    c.full_name,
                    c.email,
                    c.phone,
                    c.total_visits,
                    c.total_orders,
                    c.total_spent,
                    c.last_visit_at,
                    c.last_order_at,
                    b.business_name,
                    b.logo_url,
                    b.description,
                    b.phone,
                    b.email,
                    b.address,
                    b.city,
                    b.state,
                    b.pincode,
                    b.instagram_url,
                    b.google_review_url,
                    b.whatsapp_number
                FROM customers c
                INNER JOIN businesses b
                    ON b.id = c.business_id
                WHERE c.id = %s
                  AND c.business_id = %s
                  AND c.is_active = TRUE
                  AND b.status = 'active'
                LIMIT 1
            """, (
                customer_id,
                business_id
            ))

            customer_row = cursor.fetchone()

            if not customer_row:

                session.clear()

                flash(
                    "Your customer account could not be found.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=session.get(
                            "customer_qr_token",
                            ""
                        )
                    )
                )

            # =========================================
            # CUSTOMER DATA
            # =========================================
            customer = {
                "id": customer_row[0],
                "business_id": customer_row[1],
                "full_name": customer_row[2],
                "email": customer_row[3],
                "phone": customer_row[4],
                "total_visits": customer_row[5],
                "total_orders": customer_row[6],
                "total_spent": customer_row[7],
                "last_visit_at": customer_row[8],
                "last_order_at": customer_row[9]
            }

            # =========================================
            # BUSINESS DATA
            # =========================================
            business = {
                "id": customer_row[1],
                "business_name": customer_row[10],
                "logo_url": customer_row[11],
                "description": customer_row[12],
                "phone": customer_row[13],
                "email": customer_row[14],
                "address": customer_row[15],
                "city": customer_row[16],
                "state": customer_row[17],
                "pincode": customer_row[18],
                "instagram_url": customer_row[19],
                "google_review_url": customer_row[20],
                "whatsapp_number": customer_row[21]
            }

            # =========================================
            # TOTAL STAMPS
            # =========================================
            cursor.execute("""
                SELECT
                    COALESCE(SUM(stamp_count), 0)
                FROM loyalty_stamps
                WHERE customer_id = %s
                  AND business_id = %s
            """, (
                customer_id,
                business_id
            ))

            total_stamps = cursor.fetchone()[0] or 0

            # =========================================
            # LOYALTY SETTINGS
            # =========================================
            cursor.execute("""
                SELECT
                    minimum_order_amount,
                    stamps_per_eligible_order,
                    reward_stamps_required
                FROM loyalty_settings
                WHERE business_id = %s
                  AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """, (
                business_id,
            ))

            loyalty_row = cursor.fetchone()

            if loyalty_row:

                minimum_order_amount = (
                    loyalty_row[0] or 0
                )

                stamps_per_order = (
                    loyalty_row[1] or 1
                )

                reward_stamps_required = (
                    loyalty_row[2] or 0
                )

            else:

                minimum_order_amount = 0
                stamps_per_order = 1
                reward_stamps_required = 0

            # =========================================
            # RECENT ORDERS
            # =========================================
            cursor.execute("""
                SELECT
                    o.id,
                    o.order_number,
                    o.status,
                    o.total_amount,
                    o.payment_status,
                    o.created_at
                FROM orders o
                WHERE o.customer_id = %s
                  AND o.business_id = %s
                ORDER BY o.created_at DESC
                LIMIT 5
            """, (
                customer_id,
                business_id
            ))

            orders_rows = cursor.fetchall()

            orders = []

            for row in orders_rows:

                orders.append({
                    "id": row[0],
                    "order_number": row[1],
                    "status": row[2],
                    "total_amount": row[3],
                    "payment_status": row[4],
                    "created_at": row[5]
                })

            # =========================================
            # NEXT REWARD
            # =========================================
            next_reward = None

            if reward_stamps_required > 0:

                cursor.execute("""
                    SELECT
                        id,
                        reward_name,
                        description,
                        reward_value,
                        required_stamps,
                        validity_days
                    FROM rewards
                    WHERE business_id = %s
                      AND status = 'active'
                      AND required_stamps > %s
                    ORDER BY required_stamps ASC
                    LIMIT 1
                """, (
                    business_id,
                    total_stamps
                ))

                reward_row = cursor.fetchone()

                if reward_row:

                    next_reward = {
                        "id": reward_row[0],
                        "reward_name": reward_row[1],
                        "description": reward_row[2],
                        "reward_value": reward_row[3],
                        "required_stamps": reward_row[4],
                        "validity_days": reward_row[5]
                    }

            # =========================================
            # STAMP PROGRESS
            # =========================================
            if reward_stamps_required > 0:

                progress = min(
                    100,
                    int(
                        (
                            total_stamps
                            /
                            reward_stamps_required
                        ) * 100
                    )
                )

                remaining_stamps = max(
                    0,
                    reward_stamps_required - total_stamps
                )

            else:

                progress = 0
                remaining_stamps = 0

        # =========================================
        # UPDATE SESSION NAME
        # =========================================
        session["customer_name"] = customer["full_name"]

        # =========================================
        # RENDER
        # =========================================
        return render_template(
            "customer/home.html",
            customer=customer,
            business=business,
            orders=orders,
            total_stamps=total_stamps,
            reward_stamps_required=reward_stamps_required,
            remaining_stamps=remaining_stamps,
            progress=progress,
            next_reward=next_reward,
            minimum_order_amount=minimum_order_amount,
            stamps_per_order=stamps_per_order
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER DASHBOARD ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer dashboard failed"
        )

        flash(
            "Unable to load your account right now.",
            "danger"
        )

        return redirect(
            url_for(
                "customer_login",
                qr_token=session.get(
                    "customer_qr_token",
                    ""
                )
            )
        )

    finally:

        if connection:
            connection.close()

# ============================================================
# CUSTOMER MENU
# ============================================================

@app.route("/customer/menu")
@customer_login_required
def customer_menu():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            # BUSINESS
            cursor.execute("""
                SELECT
                    id,
                    business_name,
                    logo_url,
                    city,
                    status
                FROM businesses
                WHERE id = %s
                  AND status = 'active'
                LIMIT 1
            """, (business_id,))

            business_row = cursor.fetchone()

            if not business_row:

                qr_token = session.get("customer_qr_token", "")

                session.clear()

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=qr_token
                    )
                )

            business = {
                "id": business_row[0],
                "business_name": business_row[1],
                "logo_url": business_row[2],
                "city": business_row[3],
                "status": business_row[4]
            }

            # CATEGORIES
            cursor.execute("""
                SELECT
                    id,
                    category_name,
                    description,
                    display_order
                FROM menu_categories
                WHERE business_id = %s
                  AND is_active = TRUE
                ORDER BY
                    display_order ASC,
                    category_name ASC
            """, (business_id,))

            category_rows = cursor.fetchall()

            categories = []

            for row in category_rows:

                categories.append({
                    "id": row[0],
                    "category_name": row[1],
                    "description": row[2],
                    "display_order": row[3]
                })

            # MENU ITEMS
            cursor.execute("""
                SELECT
                    m.id,
                    m.category_id,
                    m.item_name,
                    m.description,
                    m.image_url,
                    m.price,
                    m.is_available,
                    m.display_order
                FROM menu_items m
                WHERE m.business_id = %s
                  AND m.is_active = TRUE
                ORDER BY
                    m.display_order ASC,
                    m.item_name ASC
            """, (business_id,))

            item_rows = cursor.fetchall()

            items = []

            for row in item_rows:

                items.append({
                    "id": row[0],
                    "category_id": row[1],
                    "item_name": row[2],
                    "description": row[3],
                    "image_url": row[4],
                    "price": row[5],
                    "is_available": row[6],
                    "display_order": row[7]
                })

        return render_template(
            "customer/menu.html",
            business=business,
            categories=categories,
            items=items
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER MENU ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer menu failed"
        )

        return "Unable to load menu", 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER CART
# ============================================================

@app.route("/customer/cart")
@customer_login_required
def customer_cart():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    business_name,
                    logo_url,
                    city,
                    status
                FROM businesses
                WHERE id = %s
                  AND status = 'active'
                LIMIT 1
            """, (business_id,))

            business_row = cursor.fetchone()

            if not business_row:

                qr_token = session.get(
                    "customer_qr_token",
                    ""
                )

                session.clear()

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=qr_token
                    )
                )

            business = {
                "id": business_row[0],
                "business_name": business_row[1],
                "logo_url": business_row[2],
                "city": business_row[3],
                "status": business_row[4]
            }

        return render_template(
            "customer/cart.html",
            business=business,
            customer_id=customer_id,
            business_id=business_id
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER CART ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer cart failed"
        )

        return "Unable to load cart", 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER CHECKOUT
# ============================================================

@app.route("/customer/checkout")
@customer_login_required
def customer_checkout():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            # CUSTOMER
            cursor.execute("""
                SELECT
                    id,
                    business_id,
                    full_name,
                    phone,
                    email,
                    is_active
                FROM customers
                WHERE id = %s
                  AND business_id = %s
                  AND is_active = TRUE
                LIMIT 1
            """, (
                customer_id,
                business_id
            ))

            customer_row = cursor.fetchone()

            if not customer_row:

                qr_token = session.get(
                    "customer_qr_token",
                    ""
                )

                session.clear()

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=qr_token
                    )
                )

            customer = {
                "id": customer_row[0],
                "business_id": customer_row[1],
                "full_name": customer_row[2],
                "phone": customer_row[3],
                "email": customer_row[4],
                "is_active": customer_row[5]
            }

            # BUSINESS
            cursor.execute("""
                SELECT
                    id,
                    business_name,
                    logo_url,
                    description,
                    phone,
                    email,
                    address,
                    city,
                    state,
                    pincode,
                    currency,
                    status
                FROM businesses
                WHERE id = %s
                  AND status = 'active'
                LIMIT 1
            """, (business_id,))

            business_row = cursor.fetchone()

            if not business_row:

                qr_token = session.get(
                    "customer_qr_token",
                    ""
                )

                session.clear()

                return redirect(
                    url_for(
                        "customer_login",
                        qr_token=qr_token
                    )
                )

            business = {
                "id": business_row[0],
                "business_name": business_row[1],
                "logo_url": business_row[2],
                "description": business_row[3],
                "phone": business_row[4],
                "email": business_row[5],
                "address": business_row[6],
                "city": business_row[7],
                "state": business_row[8],
                "pincode": business_row[9],
                "currency": business_row[10],
                "status": business_row[11]
            }

        return render_template(
            "customer/checkout.html",
            customer=customer,
            business=business
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER CHECKOUT ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer checkout failed"
        )

        return "Unable to load checkout", 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER PLACE ORDER
# ============================================================

@app.route("/customer/place-order", methods=["POST"])
@customer_login_required
def place_customer_order():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        data = request.get_json(silent=True) or {}

        items = data.get("items", [])

        customer_note = clean_text(
            data.get("customer_note", "")
        )

        if not items:

            return jsonify({
                "success": False,
                "message": "Your cart is empty."
            }), 400

        connection = get_db_connection()

        if not connection:
            return jsonify({
                "success": False,
                "message": "Database connection failed."
            }), 500

        with connection.cursor() as cursor:

            validated_items = []

            subtotal = 0

            # =========================================
            # VALIDATE ITEMS
            # =========================================

            for item in items:

                menu_item_id = item.get(
                    "menu_item_id"
                )

                try:
                    quantity = int(
                        item.get("quantity", 0)
                    )
                except:
                    quantity = 0

                if not menu_item_id or quantity <= 0:
                    continue

                cursor.execute("""
                    SELECT
                        id,
                        item_name,
                        price,
                        is_available
                    FROM menu_items
                    WHERE id = %s
                      AND business_id = %s
                      AND is_active = TRUE
                    LIMIT 1
                """, (
                    menu_item_id,
                    business_id
                ))

                menu_row = cursor.fetchone()

                if not menu_row:

                    connection.rollback()

                    return jsonify({
                        "success": False,
                        "message":
                            "One of the selected menu items is no longer available."
                    }), 400

                menu_item = {
                    "id": menu_row[0],
                    "item_name": menu_row[1],
                    "price": menu_row[2],
                    "is_available": menu_row[3]
                }

                if not menu_item["is_available"]:

                    connection.rollback()

                    return jsonify({
                        "success": False,
                        "message":
                            f"{menu_item['item_name']} is currently unavailable."
                    }), 400

                unit_price = float(
                    menu_item["price"]
                )

                total_price = (
                    unit_price * quantity
                )

                subtotal += total_price

                validated_items.append({
                    "menu_item_id":
                        menu_item["id"],
                    "item_name":
                        menu_item["item_name"],
                    "unit_price":
                        unit_price,
                    "quantity":
                        quantity,
                    "total_price":
                        total_price
                })

            if not validated_items:

                connection.rollback()

                return jsonify({
                    "success": False,
                    "message":
                        "No valid items found."
                }), 400

            # =========================================
            # CREATE ORDER
            # =========================================

            cursor.execute("""
                INSERT INTO orders (
                    business_id,
                    customer_id,
                    status,
                    subtotal,
                    discount_amount,
                    tax_amount,
                    delivery_charge,
                    total_amount,
                    payment_status,
                    customer_note
                )
                VALUES (
                    %s,
                    %s,
                    'pending',
                    %s,
                    0,
                    0,
                    0,
                    %s,
                    'pending',
                    %s
                )
                RETURNING
                    id,
                    order_number
            """, (
                business_id,
                customer_id,
                subtotal,
                subtotal,
                customer_note or None
            ))

            order_row = cursor.fetchone()

            if not order_row:

                connection.rollback()

                return jsonify({
                    "success": False,
                    "message":
                        "Unable to create order."
                }), 500

            order_id = order_row[0]
            order_number = order_row[1]

            # =========================================
            # ORDER ITEMS
            # =========================================

            for item in validated_items:

                cursor.execute("""
                    INSERT INTO order_items (
                        business_id,
                        order_id,
                        menu_item_id,
                        item_name,
                        unit_price,
                        quantity,
                        total_price
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    business_id,
                    order_id,
                    item["menu_item_id"],
                    item["item_name"],
                    item["unit_price"],
                    item["quantity"],
                    item["total_price"]
                ))

            # =========================================
            # UPDATE CUSTOMER
            # =========================================

            cursor.execute("""
                UPDATE customers
                SET
                    total_orders =
                        COALESCE(total_orders, 0) + 1,
                    total_spent =
                        COALESCE(total_spent, 0) + %s,
                    last_order_at =
                        CURRENT_TIMESTAMP,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE id = %s
                  AND business_id = %s
            """, (
                subtotal,
                customer_id,
                business_id
            ))

        connection.commit()

        return jsonify({
            "success": True,
            "order_id": str(order_id),
            "order_number": order_number
        })

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER PLACE ORDER ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer place order failed"
        )

        if connection:

            try:
                connection.rollback()
            except:
                pass

        return jsonify({
            "success": False,
            "message":
                "Something went wrong while placing your order."
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER ORDERS
# ============================================================

@app.route("/customer/orders")
@customer_login_required
def customer_orders():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    o.id,
                    o.order_number,
                    o.status,
                    o.total_amount,
                    o.payment_status,
                    o.created_at,
                    (
                        SELECT COUNT(*)
                        FROM order_items oi
                        WHERE oi.order_id = o.id
                          AND oi.business_id = o.business_id
                    ) AS item_count
                FROM orders o
                WHERE o.customer_id = %s
                  AND o.business_id = %s
                ORDER BY
                    o.created_at DESC
            """, (
                customer_id,
                business_id
            ))

            order_rows = cursor.fetchall()

            orders = []

            for row in order_rows:

                orders.append({
                    "id": row[0],
                    "order_number": row[1],
                    "status": row[2],
                    "total_amount": row[3],
                    "payment_status": row[4],
                    "created_at": row[5],
                    "item_count": row[6] or 0
                })

            # TOTAL SPENT
            cursor.execute("""
                SELECT
                    COALESCE(
                        SUM(total_amount),
                        0
                    )
                FROM orders
                WHERE customer_id = %s
                  AND business_id = %s
                  AND status != 'cancelled'
            """, (
                customer_id,
                business_id
            ))

            total_result = cursor.fetchone()

            total_spent = (
                total_result[0]
                if total_result
                and total_result[0] is not None
                else 0
            )

        return render_template(
            "customer/orders.html",
            orders=orders,
            total_spent=total_spent
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER ORDERS ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer orders failed"
        )

        return "Unable to load orders", 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER ORDER DETAILS
# ============================================================

@app.route("/customer/orders/<order_id>")
@customer_login_required
def customer_order_details(order_id):

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            # ORDER
            cursor.execute("""
                SELECT
                    id,
                    order_number,
                    status,
                    subtotal,
                    discount_amount,
                    tax_amount,
                    delivery_charge,
                    total_amount,
                    payment_status,
                    customer_note,
                    created_at,
                    updated_at
                FROM orders
                WHERE id = %s
                  AND customer_id = %s
                  AND business_id = %s
                LIMIT 1
            """, (
                order_id,
                customer_id,
                business_id
            ))

            order_row = cursor.fetchone()

            if not order_row:
                return "Order not found.", 404

            order = {
                "id": order_row[0],
                "order_number": order_row[1],
                "status": order_row[2],
                "subtotal": order_row[3],
                "discount_amount": order_row[4],
                "tax_amount": order_row[5],
                "delivery_charge": order_row[6],
                "total_amount": order_row[7],
                "payment_status": order_row[8],
                "customer_note": order_row[9],
                "created_at": order_row[10],
                "updated_at": order_row[11]
            }

            # ITEMS
            cursor.execute("""
                SELECT
                    id,
                    item_name,
                    unit_price,
                    quantity,
                    total_price
                FROM order_items
                WHERE order_id = %s
                  AND business_id = %s
                ORDER BY created_at ASC
            """, (
                order_id,
                business_id
            ))

            item_rows = cursor.fetchall()

            items = []

            for row in item_rows:

                items.append({
                    "id": row[0],
                    "item_name": row[1],
                    "unit_price": row[2],
                    "quantity": row[3],
                    "total_price": row[4]
                })

        return render_template(
            "customer/order_details.html",
            order=order,
            items=items
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER ORDER DETAILS ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer order details failed"
        )

        return "Unable to load order details", 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER LOYALTY
# ============================================================

@app.route("/customer/loyalty")
@customer_login_required
def customer_loyalty():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            # SETTINGS
            cursor.execute("""
                SELECT
                    reward_stamps_required
                FROM loyalty_settings
                WHERE business_id = %s
                  AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """, (business_id,))

            loyalty_row = cursor.fetchone()

            required_stamps = (
                loyalty_row[0]
                if loyalty_row
                and loyalty_row[0] is not None
                else 0
            )

            # TOTAL STAMPS
            cursor.execute("""
                SELECT
                    COALESCE(
                        SUM(stamp_count),
                        0
                    )
                FROM loyalty_stamps
                WHERE customer_id = %s
                  AND business_id = %s
            """, (
                customer_id,
                business_id
            ))

            stamp_row = cursor.fetchone()

            total_stamps = (
                stamp_row[0]
                if stamp_row
                and stamp_row[0] is not None
                else 0
            )

            # PROGRESS
            if required_stamps > 0:

                progress = min(
                    100,
                    round(
                        (
                            total_stamps
                            /
                            required_stamps
                        ) * 100,
                        2
                    )
                )

            else:

                progress = 0

            remaining_stamps = max(
                0,
                required_stamps - total_stamps
            )

            # NEXT REWARD
            cursor.execute("""
                SELECT
                    id,
                    reward_name,
                    description,
                    reward_value,
                    required_stamps,
                    validity_days
                FROM rewards
                WHERE business_id = %s
                  AND status = 'active'
                  AND required_stamps > %s
                ORDER BY
                    required_stamps ASC
                LIMIT 1
            """, (
                business_id,
                total_stamps
            ))

            reward_row = cursor.fetchone()

            next_reward = None

            if reward_row:

                next_reward = {
                    "id": reward_row[0],
                    "reward_name": reward_row[1],
                    "description": reward_row[2],
                    "reward_value": reward_row[3],
                    "required_stamps": reward_row[4],
                    "validity_days": reward_row[5]
                }

            # CLAIMED REWARDS
            cursor.execute("""
                SELECT
                    COUNT(*)
                FROM reward_claims
                WHERE customer_id = %s
                  AND business_id = %s
                  AND status = 'claimed'
            """, (
                customer_id,
                business_id
            ))

            claimed_row = cursor.fetchone()

            claimed_rewards = (
                claimed_row[0]
                if claimed_row
                and claimed_row[0] is not None
                else 0
            )

            # ELIGIBLE ORDERS
            cursor.execute("""
                SELECT
                    COUNT(*)
                FROM orders
                WHERE customer_id = %s
                  AND business_id = %s
                  AND status = 'delivered'
            """, (
                customer_id,
                business_id
            ))

            eligible_row = cursor.fetchone()

            eligible_orders = (
                eligible_row[0]
                if eligible_row
                and eligible_row[0] is not None
                else 0
            )

            # RECENT STAMPS
            cursor.execute("""
                SELECT
                    stamp_count,
                    reason,
                    created_at
                FROM loyalty_stamps
                WHERE customer_id = %s
                  AND business_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (
                customer_id,
                business_id
            ))

            stamp_rows = cursor.fetchall()

            recent_stamps = []

            for row in stamp_rows:

                recent_stamps.append({
                    "stamp_count": row[0],
                    "reason": row[1],
                    "created_at": row[2]
                })

        return render_template(
            "customer/loyalty.html",
            total_stamps=total_stamps,
            required_stamps=required_stamps,
            remaining_stamps=remaining_stamps,
            progress=progress,
            next_reward=next_reward,
            claimed_rewards=claimed_rewards,
            eligible_orders=eligible_orders,
            recent_stamps=recent_stamps
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER LOYALTY ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer loyalty failed"
        )

        return "Unable to load loyalty", 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER REWARDS
# ============================================================

@app.route("/customer/rewards")
@customer_login_required
def customer_rewards():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            # TOTAL STAMPS
            cursor.execute("""
                SELECT
                    COALESCE(
                        SUM(stamp_count),
                        0
                    )
                FROM loyalty_stamps
                WHERE customer_id = %s
                  AND business_id = %s
            """, (
                customer_id,
                business_id
            ))

            stamp_row = cursor.fetchone()

            total_stamps = (
                stamp_row[0]
                if stamp_row
                and stamp_row[0] is not None
                else 0
            )

            # AVAILABLE REWARDS
            cursor.execute("""
                SELECT
                    id,
                    reward_name,
                    description,
                    reward_value,
                    required_stamps,
                    validity_days
                FROM rewards
                WHERE business_id = %s
                  AND status = 'active'
                ORDER BY
                    required_stamps ASC,
                    created_at ASC
            """, (business_id,))

            reward_rows = cursor.fetchall()

            rewards = []

            for row in reward_rows:

                rewards.append({
                    "id": row[0],
                    "reward_name": row[1],
                    "description": row[2],
                    "reward_value": row[3],
                    "required_stamps": row[4],
                    "validity_days": row[5],
                    "can_claim":
                        total_stamps >= row[4]
                })

            # CLAIMED REWARDS
            cursor.execute("""
                SELECT
                    rc.id,
                    rc.claim_code,
                    rc.claimed_at,
                    rc.redeemed_at,
                    rc.expires_at,
                    r.reward_name
                FROM reward_claims rc
                INNER JOIN rewards r
                    ON r.id = rc.reward_id
                   AND r.business_id = rc.business_id
                WHERE rc.customer_id = %s
                  AND rc.business_id = %s
                ORDER BY
                    rc.created_at DESC
                LIMIT 10
            """, (
                customer_id,
                business_id
            ))

            claim_rows = cursor.fetchall()

            claimed_rewards = []

            for row in claim_rows:

                claimed_rewards.append({
                    "id": row[0],
                    "claim_code": row[1],
                    "claimed_at": row[2],
                    "redeemed_at": row[3],
                    "expires_at": row[4],
                    "reward_name": row[5]
                })

        return render_template(
            "customer/rewards.html",
            total_stamps=total_stamps,
            rewards=rewards,
            claimed_rewards=claimed_rewards
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER REWARDS ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer rewards failed"
        )

        return "Unable to load rewards", 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CLAIM CUSTOMER REWARD
# ============================================================

@app.route(
    "/customer/rewards/claim",
    methods=["POST"]
)
@customer_login_required
def claim_customer_reward():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        data = request.get_json(
            silent=True
        ) or {}

        reward_id = data.get("reward_id")

        if not reward_id:

            return jsonify({
                "success": False,
                "message": "Reward not selected."
            }), 400

        connection = get_db_connection()

        if not connection:

            return jsonify({
                "success": False,
                "message":
                    "Database connection failed."
            }), 500

        with connection.cursor() as cursor:

            # REWARD
            cursor.execute("""
                SELECT
                    id,
                    reward_name,
                    required_stamps,
                    validity_days,
                    status
                FROM rewards
                WHERE id = %s
                  AND business_id = %s
                LIMIT 1
            """, (
                reward_id,
                business_id
            ))

            reward_row = cursor.fetchone()

            if not reward_row:

                connection.rollback()

                return jsonify({
                    "success": False,
                    "message":
                        "Reward not found."
                }), 404

            reward = {
                "id": reward_row[0],
                "reward_name": reward_row[1],
                "required_stamps": reward_row[2],
                "validity_days": reward_row[3],
                "status": reward_row[4]
            }

            if reward["status"] != "active":

                connection.rollback()

                return jsonify({
                    "success": False,
                    "message":
                        "This reward is no longer active."
                }), 400

            # TOTAL STAMPS
            cursor.execute("""
                SELECT
                    COALESCE(
                        SUM(stamp_count),
                        0
                    )
                FROM loyalty_stamps
                WHERE customer_id = %s
                  AND business_id = %s
            """, (
                customer_id,
                business_id
            ))

            stamp_row = cursor.fetchone()

            total_stamps = (
                stamp_row[0]
                if stamp_row
                and stamp_row[0] is not None
                else 0
            )

            if total_stamps < reward["required_stamps"]:

                connection.rollback()

                remaining = (
                    reward["required_stamps"]
                    - total_stamps
                )

                return jsonify({
                    "success": False,
                    "message":
                        f"You need {remaining} more stamp(s) to claim this reward."
                }), 400

            # EXISTING CLAIM
            cursor.execute("""
                SELECT
                    id
                FROM reward_claims
                WHERE customer_id = %s
                  AND business_id = %s
                  AND reward_id = %s
                  AND status = 'claimed'
                  AND (
                      expires_at IS NULL
                      OR expires_at > CURRENT_TIMESTAMP
                  )
                LIMIT 1
            """, (
                customer_id,
                business_id,
                reward_id
            ))

            existing_claim = cursor.fetchone()

            if existing_claim:

                connection.rollback()

                return jsonify({
                    "success": False,
                    "message":
                        "You have already claimed this reward."
                }), 400

            # CLAIM CODE
            claim_code = (
                f"LL-{secrets.token_hex(4).upper()}"
            )

            # INSERT CLAIM
            if reward["validity_days"]:

                cursor.execute("""
                    INSERT INTO reward_claims (
                        business_id,
                        customer_id,
                        reward_id,
                        claim_code,
                        status,
                        claimed_at,
                        expires_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        'claimed',
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                        + (%s * INTERVAL '1 day')
                    )
                    RETURNING
                        id,
                        claim_code,
                        expires_at
                """, (
                    business_id,
                    customer_id,
                    reward_id,
                    claim_code,
                    reward["validity_days"]
                ))

            else:

                cursor.execute("""
                    INSERT INTO reward_claims (
                        business_id,
                        customer_id,
                        reward_id,
                        claim_code,
                        status,
                        claimed_at
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        'claimed',
                        CURRENT_TIMESTAMP
                    )
                    RETURNING
                        id,
                        claim_code,
                        expires_at
                """, (
                    business_id,
                    customer_id,
                    reward_id,
                    claim_code
                ))

            claim_row = cursor.fetchone()

        connection.commit()

        return jsonify({
            "success": True,
            "message":
                "Reward claimed successfully! 🎉",
            "claim_id":
                str(claim_row[0]),
            "claim_code":
                claim_row[1],
            "expires_at":
                claim_row[2],
            "redirect_url":
                url_for(
                    "customer_reward_claim",
                    claim_code=claim_row[1]
                )
        })

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER REWARD CLAIM ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer reward claim failed"
        )

        if connection:

            try:
                connection.rollback()
            except:
                pass

        return jsonify({
            "success": False,
            "message":
                "Unable to claim reward right now."
        }), 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER REVIEW
# ============================================================

@app.route("/customer/review")
@customer_login_required
def customer_review():

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    business_name,
                    logo_url,
                    description,
                    phone,
                    email,
                    address,
                    city,
                    state,
                    pincode,
                    instagram_url,
                    google_review_url,
                    whatsapp_number,
                    business_code,
                    slug,
                    status
                FROM businesses
                WHERE id = %s
                  AND status = 'active'
                LIMIT 1
            """, (business_id,))

            row = cursor.fetchone()

            if not row:

                return "Business not found.", 404

            business = {
                "id": row[0],
                "business_name": row[1],
                "logo_url": row[2],
                "description": row[3],
                "phone": row[4],
                "email": row[5],
                "address": row[6],
                "city": row[7],
                "state": row[8],
                "pincode": row[9],
                "instagram_url": row[10],
                "google_review_url": row[11],
                "whatsapp_number": row[12],
                "business_code": row[13],
                "slug": row[14],
                "status": row[15]
            }

        return render_template(
            "customer/review.html",
            business=business
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER REVIEW ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer review failed"
        )

        return "Unable to load review page.", 500

    finally:

        if connection:
            connection.close()


# ============================================================
# CUSTOMER REWARD CLAIM DETAILS
# ============================================================

@app.route(
    "/customer/reward-claim/<claim_code>"
)
@customer_login_required
def customer_reward_claim(claim_code):

    customer_id = session.get("customer_id")
    business_id = session.get("customer_business_id")

    connection = None

    try:

        connection = get_db_connection()

        if not connection:
            return "Database connection failed.", 500

        with connection.cursor() as cursor:

            cursor.execute("""
                SELECT
                    rc.id,
                    rc.claim_code,
                    rc.status,
                    rc.claimed_at,
                    rc.redeemed_at,
                    rc.expires_at,
                    r.id,
                    r.reward_name,
                    r.description,
                    r.reward_value,
                    r.required_stamps,
                    r.validity_days
                FROM reward_claims rc
                INNER JOIN rewards r
                    ON r.id = rc.reward_id
                   AND r.business_id = rc.business_id
                WHERE rc.claim_code = %s
                  AND rc.customer_id = %s
                  AND rc.business_id = %s
                LIMIT 1
            """, (
                claim_code,
                customer_id,
                business_id
            ))

            row = cursor.fetchone()

            if not row:

                return "Reward claim not found.", 404

            claim = {
                "id": row[0],
                "claim_code": row[1],
                "status": row[2],
                "claimed_at": row[3],
                "redeemed_at": row[4],
                "expires_at": row[5]
            }

            reward = {
                "id": row[6],
                "reward_name": row[7],
                "description": row[8],
                "reward_value": row[9],
                "required_stamps": row[10],
                "validity_days": row[11]
            }

        return render_template(
            "customer/reward_claim.html",
            claim=claim,
            reward=reward
        )

    except Exception as error:

        print("\n========================================")
        print("CUSTOMER REWARD CLAIM PAGE ERROR")
        print("========================================")
        print(error)
        print("========================================\n")

        app.logger.exception(
            "Customer reward claim page failed"
        )

        return "Unable to load reward claim.", 500

    finally:

        if connection:
            connection.close()



@app.route("/customer/logout")
def customer_logout():

    qr_token = session.get("customer_qr_token")

    session.clear()

    if qr_token:
        return redirect(
            url_for(
                "customer_login",
                qr_token=qr_token
            )
        )

    return redirect("/")

if __name__=="__main__":
    print("\n"+"="*55)
    print("             LoyalLoop Backend 🚀")
    print("="*55)

    connection=get_db_connection()

    if connection:
        print("PostgreSQL Connected Successfully! ✅")
        connection.close()
    else:
        print("PostgreSQL Connection Failed! ❌")

    print("="*55)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )