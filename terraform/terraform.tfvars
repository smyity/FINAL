# эти переменные также нужно объявить в файле global_variables.tf, но только их тип
cloud_id = "b1gc3k00qi2fi08ed282"
folder_id = "b1gbhs59559ntu7hvlcn"
vm_image_OS = "ubuntu-2204-lts"

# переменные для сети
name_vpc_network = "devops-finallity"
name_default_vpc_subnet_zone = "geozone-a"
default_zone = "ru-central1-a"
default_zone_cidr_blocks = ["10.0.1.0/24"]

# переменные для ВМ
vm_name = "final-infrastructure"
use_public_ip = true
vm_resourses = {
    cores         = 4
    memory        = 10
    core_fraction = 20
    disk_size     = 50
}

# переменные пользователя
username = "osho"
path_ssh_key = "~/.ssh/ssh-key-1759501063847"
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCng7JNHRuQCrIY4sPVlVHRb+jaAHdRnx/ZPT9FYgxTd3MbECxqNTYldRGeaWAn/fzf6ixIv5A8VfB1kM6yxbmkWE6DM9GKsk2QMe/ikaTR06OEJEwfPyKf7pKTXRIm2VG0+Y5lzu3RfapAzsLkxS3tAMT1dbnfQW2IxzrybmPApe3vdDwHoAoThQ6yp3M1/cO3VADv3znTaLs/lLwGanTjAf22PetJm0lZwA/e6hho9yHanAAzYQn1gzzaXA5k7jaIU88pXwSY0jGlrbs/dk4dbMEJ5KpfxNEYq3/KCRfe02BOLj5EEigHxZ2EsHizsoiKwJM8ULFXQFvGvQ9FDqVV"
