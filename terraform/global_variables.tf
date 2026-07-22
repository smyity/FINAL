variable "cloud_id" { type = string }
variable "folder_id" { type = string }
variable "vm_image_OS" { type = string }

# переменные для сети
variable "name_vpc_network" { type = string }
variable "name_default_vpc_subnet_zone" { type = string }
variable "default_zone" { type = string }
variable "default_zone_cidr_blocks" { type = list(string) }

# переменные для ВМ
variable "vm_name" { type = string }
variable "use_public_ip" { type = bool }
variable "vm_resourses" {
  description = "выделение ресурсов для ВМ"
  type        = map(number)
}

# переменные пользователя
variable "username" { type = string }
variable "path_ssh_key" { type = string }
variable "ssh_public_key" { type = string }
