from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2

app = Flask(__name__)
app.secret_key = 'chave_secreta'

# Função de conexão com o banco de dados
def conectar():
    try:
        conn = psycopg2.connect(
            dbname="passagem", user="postgres", password="postgres", host="localhost", port="5432"
        )
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

@app.route('/')
def index():
    conn = conectar()
    if conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, origem, destino, data_partida FROM viagens;")
        viagens = cursor.fetchall()

        cursor.execute("""
            SELECT p.id, p.numero, v.origem, v.destino, 
                   COALESCE(r.status, 'disponível') AS status,
                   r.id AS reserva_id
            FROM poltronas p
            JOIN viagens v ON p.viagem_id = v.id
            LEFT JOIN reservas r ON p.id = r.poltrona_id;
        """)
        poltronas = cursor.fetchall()

        cursor.close()
        conn.close()
        return render_template("index.html", viagens=viagens, poltronas=poltronas)
    return "Erro ao conectar ao banco", 500

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']

        conn = conectar()
        if conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO usuarios (nome, email) VALUES (%s, %s) RETURNING id;", (nome, email))
            usuario_id = cursor.fetchone()[0]  # Pegando o ID corretamente
            
            session['usuario_id'] = usuario_id  # Salvando ID na sessão
            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for('index'))

    return render_template('cadastro.html')

@app.route('/reservar', methods=['POST'])
def reservar_poltrona():
    usuario_id = session.get('usuario_id')
    
    if not usuario_id:
        return redirect(url_for('cadastro'))

    poltrona_id = request.form.get('poltrona_id')

    conn = conectar()
    if conn:
        cursor = conn.cursor()

        # Verificando se o usuário realmente existe antes de reservar
        cursor.execute("SELECT id FROM usuarios WHERE id = %s;", (usuario_id,))
        if cursor.fetchone() is None:
            return redirect(url_for('cadastro'))

        try:
            cursor.execute("""
                INSERT INTO reservas (usuario_id, poltrona_id, status)
                VALUES (%s, %s, 'reservado')
                RETURNING id;
            """, (usuario_id, poltrona_id))
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            return f"Erro ao reservar poltrona: {e}", 500
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('index'))
    
    return "Erro ao reservar poltrona", 500

@app.route('/cancelar/<int:reserva_id>')
def cancelar_reserva(reserva_id):
    conn = conectar()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reservas SET status = 'cancelado' WHERE id = %s AND status = 'reservado';
        """, (reserva_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    return "Erro ao cancelar reserva", 500

@app.route('/confirmar/<int:reserva_id>')
def confirmar_finalizacao(reserva_id):
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return redirect(url_for('cadastro'))

    conn = conectar()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, u.nome, p.numero, v.origem, v.destino
            FROM reservas r
            JOIN usuarios u ON r.usuario_id = u.id
            JOIN poltronas p ON r.poltrona_id = p.id
            JOIN viagens v ON p.viagem_id = v.id
            WHERE r.id = %s;
        """, (reserva_id,))
        reserva = cursor.fetchone()
        cursor.close()
        conn.close()
        if reserva:
            return render_template('confirmacao.html', reserva=reserva)
    return "Reserva não encontrada", 404

@app.route('/finalizar/<int:reserva_id>')
def finalizar_compra(reserva_id):
    conn = conectar()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reservas SET status = 'finalizado' WHERE id = %s AND status = 'reservado';
        """, (reserva_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
    return "Erro ao finalizar compra", 500

if __name__ == '__main__':
    app.run(debug=True)











