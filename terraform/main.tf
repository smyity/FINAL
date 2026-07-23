# --- PROVIDERS --- #
terraform {
  required_providers {
    yandex = {
      source = "yandex-cloud/yandex"
    }
  }
}

provider "yandex" {
  cloud_id                 = var.cloud_id
  folder_id                = var.folder_id
  service_account_key_file = file("~/.authorized_key.json")
}


# --- СЕТЬ --- #
# облачная сеть
resource "yandex_vpc_network" "devops" {
  name = var.name_vpc_network
}
# подсеть
resource "yandex_vpc_subnet" "devops_a" {
  name           = var.name_default_vpc_subnet_zone
  zone           = var.default_zone
  network_id     = yandex_vpc_network.devops.id
  v4_cidr_blocks = var.default_zone_cidr_blocks
}


# --- ОБРАЗ --- #
data "yandex_compute_image" "ubuntu" {
  family = var.vm_image_OS
}


# --- ВМ --- #
resource "yandex_compute_instance" "vm" {
  name           = var.vm_name
  hostname       = var.vm_name
  zone           = var.default_zone
  platform_id    = "standard-v3"
  resources {
    cores         = var.vm_resourses["cores"]
    memory        = var.vm_resourses["memory"]
    core_fraction = var.vm_resourses["core_fraction"]
  }
  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.image_id
      type     = "network-hdd"
      size     = var.vm_resourses["disk_size"]
    }
  }
  scheduling_policy { preemptible = var.stoppable_vm }
  network_interface {
    subnet_id = yandex_vpc_subnet.devops_a.id
    nat       = var.use_public_ip
  }

  metadata = {
    user-data          = data.template_file.cloudinit.rendered
    serial-port-enable = 1
  }
}

# --- СОЗДАНИЕ ФАЙЛА ПО ШАБЛОНУ --- #
data "template_file" "cloudinit" {
  template = file("./cloud-init.yml")
  vars = {
    username       = var.username
    ssh_public_key = var.ssh_public_key 
  }
}


# --- СОЗДАНИЕ ФАЙЛА INVENTORY.INI ДЛЯ ANSIBLE --- #
resource "local_file" "inventory" {
  filename = "./inventory.ini"

  content  = <<-EOF
[VM]
target-vm ansible_host=${yandex_compute_instance.vm.network_interface[0].nat_ip_address} ansible_user=${var.username} ansible_ssh_private_key_file=${var.path_ssh_key} ansible_ssh_common_args="-o StrictHostKeyChecking=no"
EOF
  depends_on = [ yandex_compute_instance.vm ]
}


resource "terraform_data" "ansible_bootstrap" {
  # запускаем после создания файла inventory.ini
  depends_on = [local_file.inventory]

  provisioner "local-exec" {
    command = <<EOT
      echo "Waiting to run SSH on VM..."
      until nc -z -v -w5 ${yandex_compute_instance.vm.network_interface[0].nat_ip_address} 22; do
        echo "SSH not available, wait 5 seconds..."
        sleep 5
      done
      echo "SSH available! Run Ansible Playbook..."
      ansible-playbook -i ./inventory.ini deploy_infrastructure.yml
    EOT
  }
}
