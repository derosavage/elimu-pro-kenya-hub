def register_blueprints(app):
    from .auth import bp as auth
    from .schools import bp as schools
    from .admissions import bp as admissions
    from .students import bp as students
    from .academics import bp as academics
    from .finance import bp as finance
    from .announcements import bp as announcements
    from .teachers import bp as teachers
    from .parents import bp as parents
    for bp in (auth, schools, admissions, students, academics, finance, announcements, teachers, parents):
        app.register_blueprint(bp)
