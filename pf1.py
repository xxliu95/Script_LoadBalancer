#!/usr/bin/python
# Alumnos:
# Xinxin Liu
# Fco. Romulo Ballero Garijo
import os
import sys
import argparse

from lxml import etree

def parse_args():
    parser = argparse.ArgumentParser(description='CREACION AUTOMATICA DE UN ESCENARIO DEL BALANCEADOR DE CARGA', add_help=False)

    group1 = parser.add_argument_group('numero de servidores')
    group1.add_argument('N', default=2, nargs="?",type=int, help='N servidores, siendo N el argumento entre 1-5')

    group2 = parser.add_mutually_exclusive_group() # solo se puede elegir una opcion de las siguientes a la vez
    group2.add_argument('-c','--crear',action='store_true', help='Crea un escenario con N servidores (por defecto N=2)')
    group2.add_argument('-a','--arrancar', metavar=("id"), help='Arranca la maquina ID')
    group2.add_argument('-p','--parar', metavar=("id"), help='Para la maquina ID')
    group2.add_argument('-ae', action='store_true', help='Arranca el escenario')
    group2.add_argument('-pe', action='store_true', help='Para el escenario')
    group2.add_argument('-d','--destruir', action='store_true', help='Elimina el escenario y todos los ficheros creados')
    group2.add_argument('-m','--monitor', action='store_true', help='Monitoriza los estados de las maquinas')

    group2.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Muestra este mensaje de ayuda.')
    return parser.parse_args()

# Parte 1 crear
def crearLB():
    os.system("qemu-img create -f qcow2 -b cdps-vm-base-pf1.qcow2 lb.qcow2")
    os.system("cp plantilla-vm-pf1.xml lb.xml")

    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse("lb.xml", parser)
    #print etree.tostring(tree, pretty_print=True)

    root = tree.getroot()
    name = root.find("name")
    name.text = "lb"

    disk = root.find("./devices/disk/source")
    disk.set("file", "{}/lb.qcow2".format(os.getcwd()))

    source1 = root.find("./devices/interface/source")
    source1.set("bridge", "LAN1")

    devices = root.find("./devices")
    interface2 = etree.SubElement(devices, "interface")
    source2 = etree.SubElement(interface2, "source")
    model2 = etree.SubElement(interface2, "model")
    interface2.set("type", "bridge")
    source2.set("bridge", "LAN2")
    model2.set("type", "virtio")
    interface1 = root.find("./devices/interface")
    interface1.addnext(interface2)

    with open("lb.xml", "w") as f:
        f.write(etree.tostring(tree, pretty_print=True))
    #print etree.tostring(tree, pretty_print=True)

    os.system("sudo virsh define lb.xml")

    # fichero hostname
    with open("hostname", "w") as f:
        f.write("lb\n")
    os.system("sudo virt-copy-in -a lb.qcow2 hostname /etc")
    os.system("rm hostname")

    # fichero hosts
    with open("hosts", "w") as f:
        f.writelines(["127.0.1.1 lb\n", "127.0.0.1 localhost\n",
                    "::1 ip6-localhost ip6-loopback\n", "fe00::0 ip6-localnet\n",
                    "ff00::0 ip6-mcastprefix\n", "ff02::1 ip6-allnodes\n",
                    "ff02::2 ip6-allrouters\n", "ff02::3 ip6-allhosts\n"])

    os.system("sudo virt-copy-in -a lb.qcow2 hosts /etc")
    os.system("rm hosts")

    # fichero interfaces
    with open("interfaces", "w") as f:
        f.writelines(["auto lo\n","iface lo inet loopback\n","auto eth0\n",
                "iface eth0 inet dhcp\n","iface eth0 inet static\n",
                "address 10.0.1.1\n","netmask 255.255.255.0\n","gateway 10.0.1.1\n",
                "dns-nameservers 10.0.1.1\n","auto eth1\n","iface eth1 inet static\n",
                "address 10.0.2.1\n","netmask 255.255.255.0\n","gateway 10.0.2.1\n",
                "dns-nameservers 10.0.2.1\n"])

    os.system("sudo virt-copy-in -a lb.qcow2 interfaces /etc/network")
    os.system("rm interfaces")

    # fichero sysctl.conf
    with open("sysctl.conf", "w") as f:
        f.write("net.ipv4.ip_forward=1\n")
    os.system("sudo virt-copy-in -a lb.qcow2 sysctl.conf /etc")
    os.system("rm sysctl.conf")

    # fichero haproxy.cfg
    N = leerN()
    with open("haproxy.cfg", "w") as f:
        f.writelines([
                "global\n",
                "log /dev/log    local0\n",
                "log /dev/log    local1 notice\n","chroot /var/lib/haproxy\n",
                "stats socket /run/haproxy/admin.sock mode 660 level admin expose-fd listeners\n",
                "stats timeout 30s\n","user haproxy\n","group haproxy\n","daemon\n",
                "ca-base /etc/ssl/certs\n","crt-base /etc/ssl/private\n",
                "ssl-default-bind-ciphers ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:RSA+AESGCM:RSA+AES:!aNULL:!MD5:!DSS\n",
                "ssl-default-bind-options no-sslv3\n",
                "defaults\n","log    global\n","mode    http\n",
                "option    httplog\n","option    dontlognull\n","timeout connect 5000\n",
                "timeout client  50000\n","timeout server  50000\n","errorfile 400 /etc/haproxy/errors/400.http\n",
                "errorfile 403 /etc/haproxy/errors/403.http\n","errorfile 408 /etc/haproxy/errors/408.http\n",
                "errorfile 500 /etc/haproxy/errors/500.http\n","errorfile 502 /etc/haproxy/errors/502.http\n",
                "errorfile 503 /etc/haproxy/errors/503.http\n","errorfile 504 /etc/haproxy/errors/504.http\n",
                "frontend lb\n",
                "bind *:80\n","mode http\n","default_backend webservers\n",
                "backend webservers\n",
                "mode http\n","balance roundrobin\n"])
        for x in range(1,N+1):
            f.write("server s{} 10.0.2.1{}:80 check\n".format(x,x))

    os.system("sudo virt-copy-in -a lb.qcow2 haproxy.cfg /etc/haproxy")
    os.system("rm haproxy.cfg")


def crearC1():
    os.system("qemu-img create -f qcow2 -b cdps-vm-base-pf1.qcow2 c1.qcow2")
    os.system("cp plantilla-vm-pf1.xml c1.xml")

    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse("c1.xml", parser)

    root = tree.getroot()
    name = root.find("name")
    name.text = "c1"

    disk = root.find("./devices/disk/source")
    disk.set("file", "{}/c1.qcow2".format(os.getcwd()))

    source1 = root.find("./devices/interface/source")
    source1.set("bridge", "LAN1")

    with open("c1.xml", "w") as f:
        f.write(etree.tostring(tree, pretty_print=True))

    os.system("sudo virsh define c1.xml")

    with open("hostname", "w") as f:
        f.write("c1\n")
    os.system("sudo virt-copy-in -a c1.qcow2 hostname /etc")
    os.system("rm hostname")

    with open("hosts", "w") as f:
        f.writelines(["127.0.1.1 c1\n", "127.0.0.1 localhost\n",
                    "::1 ip6-localhost ip6-loopback\n", "fe00::0 ip6-localnet\n",
                    "ff00::0 ip6-mcastprefix\n", "ff02::1 ip6-allnodes\n",
                    "ff02::2 ip6-allrouters\n", "ff02::3 ip6-allhosts\n"])

    os.system("sudo virt-copy-in -a c1.qcow2 hosts /etc")
    os.system("rm hosts")

    with open("interfaces", "w") as f:
        f.writelines(["auto lo\n","iface lo inet loopback\n","auto eth0\n",
                "iface eth0 inet dhcp\n","iface eth0 inet static\n",
                "address 10.0.1.2\n","netmask 255.255.255.0\n","gateway 10.0.1.1\n",
                "dns-nameservers 10.0.1.1\n"])

    os.system("sudo virt-copy-in -a c1.qcow2 interfaces /etc/network")
    os.system("rm interfaces")

def crearServ(N):
    for x in range(1,N+1):
        os.system("qemu-img create -f qcow2 -b cdps-vm-base-pf1.qcow2 s{}.qcow2".format(x))
        os.system("cp plantilla-vm-pf1.xml s{}.xml".format(x))

        tree = etree.parse("s{}.xml".format(x))
        #print etree.tostring(tree, pretty_print=True)

        root = tree.getroot()
        name = root.find("name")
        name.text = "s{}".format(x)

        disk = root.find("./devices/disk/source")
        disk.set("file", "{}/s{}.qcow2".format(os.getcwd(),x))

        interface1 = root.find("./devices/interface/source")
        interface1.set("bridge", "LAN2")

        with open("s{}.xml".format(x), "w") as f:
            f.write(etree.tostring(tree, pretty_print=True))
        #print etree.tostring(tree, pretty_print=True)

        os.system("sudo virsh define s{}.xml".format(x))

        # fichero hostname
        with open("hostname", "w") as f:
            f.write("s{}\n".format(x))
        os.system("sudo virt-copy-in -a s{}.qcow2 hostname /etc".format(x))
        os.system("rm hostname")

        # fichero hosts
        with open("hosts", "w") as f:
            f.writelines(["127.0.1.1 s{}\n".format(x), "127.0.0.1 localhost\n",
                        "::1 ip6-localhost ip6-loopback\n", "fe00::0 ip6-localnet\n",
                        "ff00::0 ip6-mcastprefix\n", "ff02::1 ip6-allnodes\n",
                        "ff02::2 ip6-allrouters\n", "ff02::3 ip6-allhosts\n"])

        os.system("sudo virt-copy-in -a s{}.qcow2 hosts /etc".format(x))
        os.system("rm hosts")

        # fichero interfaces
        with open("interfaces", "w") as f:
            f.writelines(["auto lo\n","iface lo inet loopback\n","auto eth0\n",
                    "iface eth0 inet dhcp\n","iface eth0 inet static\n",
                    "address 10.0.2.1{}\n".format(x),"netmask 255.255.255.0\n","gateway 10.0.2.1\n",
                    "dns-nameservers 10.0.2.1\n"])

        os.system("sudo virt-copy-in -a s{}.qcow2 interfaces /etc/network".format(x))
        os.system("rm interfaces")

        # fichero index.html
        with open("index.html", "w") as f:
            f.write("S{}\n".format(x))
        os.system("sudo virt-copy-in -a s{}.qcow2 index.html /var/www/html".format(x))
        os.system("rm index.html")

def leerN():
    N = 0
    try:
        with open("pf1.cfg") as f:
            N = int(f.read().split("=")[1])
    except IOError:
        print("No existe el fichero pf1.cfg")
    return N

def crear(N):
    print("creando {} servidores".format(N))
    with open("pf1.cfg", "w") as f:
        f.write("num_serv={}".format(N))
    os.system("sudo brctl addbr LAN1")
    os.system("sudo brctl addbr LAN2")
    os.system("sudo ifconfig LAN1 up")
    os.system("sudo ifconfig LAN2 up")
    os.system("sudo ifconfig LAN1 10.0.1.3/24")
    os.system("sudo ip route add 10.0.0.0/16 via 10.0.1.1")

    crearLB()
    crearC1()
    crearServ(N)

# Parte 2 arrancar
def arrancarEscenario():
    N = leerN()

    for x in range(1,N+1):
        os.system("sudo virsh start s{}".format(x))
        os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 's{}' -e 'sudo virsh console s{}' &".format(x,x))

    os.system("sudo virsh start lb")
    os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 'lb' -e 'sudo virsh console lb' &")

    os.system("sudo virsh start c1")
    os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 'c1' -e 'sudo virsh console c1' &")

# Parte 3 parar
def pararEscenario():
    N = leerN()

    for x in range(1,N+1):
        os.system("sudo virsh shutdown s{}".format(x))

    os.system("sudo virsh shutdown lb")
    os.system("sudo virsh shutdown c1")

# Parte 4 destruir
def destruir():
    N = leerN()

    for x in range(1,N+1):
        os.system("sudo virsh undefine s{}".format(x))
        os.system("rm -f s{}.qcow2".format(x))
        os.system("rm -f s{}.xml".format(x))

    os.system("sudo virsh undefine lb")
    os.system("rm -f lb.qcow2")
    os.system("rm -f lb.xml")

    os.system("sudo virsh undefine c1")
    os.system("rm -f c1.qcow2")
    os.system("rm -f c1.xml")

    os.system("rm -f pf1.cfg")

# Parte opcional 1 monitorizacion
def monitor():
    N = leerN()
    command = "sudo virsh dominfo lb && sudo virsh dominfo c1"
    for x in range(1,N+1):
        command += " && sudo virsh dominfo s{}".format(x)
    os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title 'Monitor' -e 'watch \"{}\"' &".format(command))
    return

# Parte opcional 2 arrancar y parar MV individualmente
def arrancar(id):
    os.system("sudo virsh start {}".format(id))
    os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title '{}' -e 'sudo virsh console {}' &".format(id,id))

def parar(id):
    os.system("sudo virsh shutdown {}".format(id))

# __main__
if __name__ == '__main__':
    args = parse_args()

    if args.N > 5 or args.N < 1:
        print("El argumento tiene que ser entre 1-5")
        sys.exit()

    if args.crear:
        crear(args.N)

    if args.ae:
        arrancarEscenario()

    if args.pe:
        pararEscenario()

    if args.arrancar:
        arrancar(args.arrancar)

    if args.parar:
        parar(args.parar)

    if args.destruir:
        destruir()

    if args.monitor:
        monitor()
