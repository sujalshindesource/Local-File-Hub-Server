from flask import Flask, request, jsonify
import os, shutil, subprocess, platform, time
from flask_cors import CORS 
app = Flask(__name__)
CORS(app) 
@app.route("/file", methods=["POST"])
def file_operations():
    data = request.json
    operation = data.get("operation")
    path = data.get("path")
    filename = data.get('filename')
    abspath = path + f'/{filename}'
    print(abspath)

    try:
        if operation == "list":
            return jsonify({"files": os.listdir(path)})

        elif operation == "open":
            if platform.system() == "Windows":
                os.startfile(abspath)
                return jsonify({"stauts" : 'jhal ka bgh open'})
            elif platform.system() == "Darwin":
                subprocess.call(["open", abspath])
            else:
                subprocess.call(["xdg-open", abspath])
            return jsonify({"status": "opened"})

        elif operation == "delete":
            if os.path.isfile(abspath):
                os.remove(abspath)
            else:
                shutil.rmtree(paabspathth)
            return jsonify({"status": "deleted"})

        elif operation == "copy":
            dst = data.get("destination")
            if os.path.isdir(abspath):
                shutil.copytree(abspath, dst)
            else:
                shutil.copy2(abspath, dst)
            return jsonify({"status": "copied"})

        elif operation == "move":
            dst = data.get("destination")
            shutil.move(abspath, dst)
            return jsonify({"status": "moved"})

        elif operation == "rename":
            new_name = data.get("new_name")
            new_path = os.path.join(os.path.dirname(abspath), new_name)
            os.rename(abspath, new_path)
            return jsonify({"status": "renamed", "new_path": new_path})

        elif operation == "create_file":
            open(abspath, "w").close()
            return jsonify({"status": "file_created"})

        elif operation == "create_folder":
            os.makedirs(abspath, exist_ok=True)
            return jsonify({"status": "folder_created"})

        else:
            return jsonify({"error": "unknown operation"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
