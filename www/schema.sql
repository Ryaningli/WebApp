-- schema.sql

DROP USER 'ryan';
CREATE USER 'ryan'@'%' IDENTIFIED BY '1116';
grant select, insert, update, delete on awesome.* to 'ryan'@'%';

DROP DATABASE IF EXISTS awesome;
CREATE DATABASE awesome;

USE awesome;

create table users (
    `id` varchar(50) not null,
    `phone` varchar(50) not null,
    `email` varchar(50),
    `password` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `create_time` datetime not null,
    unique key `idx_phone` (`phone`),
    key `idx_create_time` (`create_time`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs (
    `id` int(10) not null auto_increment,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `name` varchar(50) not null,
    `summary` varchar(200) not null,
    `content` mediumtext not null,
    `create_time` datetime not null,
    `update_time` datetime not null,
    key `idx_create_time` (`create_time`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
    `id` int(10) not null auto_increment,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `create_time` datetime not null,
    key `idx_create_time` (`create_time`),
    primary key (`id`)
) engine=innodb default charset=utf8;

-- 执行脚本
-- mysql -u root -p1116 < schema.sql