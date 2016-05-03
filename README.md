
Datal
=====
Plataforma de publicación de Datos Abiertos de código abierto bajo licencia BSD 3.


Herramientas
------------

Vangrant: https://www.vagrantup.com/

VirtualBox: https://www.virtualbox.org/

En Windows también se debe instalar GIT: http://git-scm.com/download/win

Instalacion sin vagrant
-----------------------

curl -L https://raw.githubusercontent.com/datal-org/datal/master/install.py | python


Instalacion en vagrant
----------------------

Luego de haber clonado el repositorio, dentro del mismo ejecutar:

1. Agregar los siguientes hosts a nuestro archivo de hosts apuntando a localhost. Ejemplo suponiendo que el IP local es 127.0.0.1

    127.0.0.1 admin.dev api.dev datastore.dev microsite.dev microsites.dev  workspace.dev

2. Iniciar la virtual con el comando:

    vagrant up --provision

3. Iniciar el servicio Web:

    vagrant ssh
    
    sudo supervisorctl start uwsgi

4. Para probar la demo, en tu navegador ingresá a http://workspace.dev:8080/


Usuarios y claves para acceder a la demo
----------------------------------------

Administrador: administrador/administrador

Editor: editor/editor

Publicador: publicador/publicador


Acceso a la virtual
-------------------


Para acceder a la virtual via SSH

  vagrant ssh


Logs
----
  UWSGI: /var/log/uwsgi/uwsgi-workspace.log
  
  DJANGO: /tmp/datal.log
    
  MOTOR (TOMCAT): /var/log/tomcat7/catalina.out
  
  CORREOS: /tmp/datal-emails/
  
  NGINX: /var/log/nginx/


Actualizacion
-------------

1. git pull origin master
2. vagrant provision (si la virtual esta corriendo) o vagrant up --provision (si la virtual esta apagada)


Personalización de aspectos gráficos
---------

Para ajustar los estilos gráficos del espacio de trabajo es necesario editar el archivo '_variables.scss'. Dentro de este 
archivo SASS se encuentran las variables necesarias para personalizar la identidad visual de Datal. 

Ejemplo:

    $brand-color: blue;				/* Brand primary color */


SASS: http://sass-lang.com/

Documentación SASS: http://sass-lang.com/documentation/file.SASS_REFERENCE.html


Releases
--------


Pude ver la información de cada release en https://github.com/datal-org/datal/releases
