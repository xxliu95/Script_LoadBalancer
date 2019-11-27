#!/usr/bin/python
import os
import sys
import argparse

from lxml import etree

def parse_args():
    parser = argparse.ArgumentParser(description='DESARROLLO DE UN SCRIPT PARA LA CREACION AUTOMATICA DEL ESCENARIO DEL BALANCEADOR DE LA PRACTICA 3', add_help=False)

    group1 = parser.add_argument_group('numero de servidores')
    group1.add_argument('N', default=2, nargs="?",type=int, help='N servidores, siendo N el argumento entre 1-5')

    group2 = parser.add_mutually_exclusive_group() # solo se puede elegir una opcion de las siguientes a la vez
    group2.add_argument('-c','--crear',action='store_true', help='Crea un escenario con N servidores (por defecto N=2)')
    group2.add_argument('-a','--arrancar', action='store_true', help='Arranca el escenario')
    group2.add_argument('-p','--parar', action='store_true', help='Para el escenario')
    group2.add_argument('-d','--destruir', action='store_true', help='Elimina el escenario y todos los ficheros creados')

    group2.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
    help='Muestra este mensaje de ayuda.')
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
    disk.set("file", "/mnt/tmp/pf1/lb.qcow2")

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
        disk.set("file", "/mnt/tmp/pf1/s{}.qcow2".format(x))

        interface1 = root.find("./devices/interface/source")
        interface1.set("bridge", "LAN2")

        with open("s{}.xml".format(x), "w") as f:
            f.write(etree.tostring(tree, pretty_print=True))
        #print etree.tostring(tree, pretty_print=True)

        os.system("sudo virsh define s{}.xml".format(x))

def leerN():
    N = 0
    try:
        with open("pf1.cfg") as f:
            N = int(f.read().split("=")[1])
    except IOError:
        print("No existe el fichero pf1.cfg")
    return N

def crear(N):
    print("creadno {} servidores".format(N))
    with open("pf1.cfg", "w") as f:
        f.write("num_serv={}".format(N))
    os.system("sudo brctl addbr LAN1")
    os.system("sudo brctl addbr LAN2")
    os.system("sudo ifconfig LAN1 up")
    os.system("sudo ifconfig LAN2 up")
    crearLB()
    crearServ(N)

def arrancar():
    N = leerN()

    for x in range(1,N+1):
        os.system("sudo virsh start s{}".format(x))

    os.system("sudo virsh start lb")

def parar():
    N = leerN()

    for x in range(1,N+1):
        os.system("sudo virsh shutdown s{}".format(x))

    os.system("sudo virsh shutdown lb")

def destruir():
    N = leerN()

    for x in range(1,N+1):
        os.system("sudo virsh destroy s{}".format(x))
        os.system("sudo virsh undefine s{}".format(x))
        #os.system("sudo virsh vol-delete --pool vg0 s{}.qcow2".format(x))

    os.system("sudo virsh destroy lb")
    os.system("sudo virsh undefine lb")
    #os.system("sudo virsh vol-delete --pool vg0 lb.qcow2")


if __name__ == '__main__':
    args = parse_args()

    if args.N > 5 or args.N < 1:
        print("El argumento tiene que ser entre 1-5")
        sys.exit()

    if args.crear:
        crear(args.N)

    if args.arrancar:
        arrancar()

    if args.parar:
        parar()

    if args.destruir:
        destruir()
