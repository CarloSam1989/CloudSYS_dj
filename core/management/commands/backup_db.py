import os
import datetime
import subprocess
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Genera backup PostgreSQL y lo envía al superusuario"

    def handle(self, *args, **kwargs):
        db = settings.DATABASES['default']

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.sql"
        backup_path = os.path.join(settings.BASE_DIR, backup_filename)

        # Variables necesarias para pg_dump
        os.environ['PGPASSWORD'] = db['PASSWORD']

        command = [
            "pg_dump",
            "-h", db['HOST'],
            "-U", db['USER'],
            "-d", db['NAME'],
            "-F", "c",  # formato custom (más seguro y comprimido)
            "-f", backup_path
        ]

        try:
            subprocess.run(command, check=True)

            # Obtener superusuario
            User = get_user_model()
            admin = User.objects.filter(is_superuser=True).first()

            if admin and admin.email:
                email = EmailMessage(
                    subject="Backup automático PostgreSQL",
                    body="Adjunto se encuentra el respaldo automático del sistema.",
                    from_email=settings.EMAIL_HOST_USER,
                    to=[admin.email],
                )

                email.attach_file(backup_path)
                email.send()

                self.stdout.write(self.style.SUCCESS("Backup generado y enviado correctamente"))

            else:
                self.stdout.write(self.style.WARNING("No se encontró superusuario con email"))

            # Eliminar archivo después de enviar
            os.remove(backup_path)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error en backup: {e}"))
