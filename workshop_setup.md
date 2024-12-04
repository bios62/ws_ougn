# Workshop setup
The workshop can be configured on any autonomous database.   
Configure the pl/sql script config_workshop.sql.   
Do not save your version of the script on git, as the password is coded in the pl/sql package.
Example config:  
```set serveroutput on
create or replace package lab_config as
--
--  Package that configures the PL/SQL creating the workshop
--  Run prior to user creation or workspace creation, set defaults
--  (c) Inge Os 2024
--  29.08.24
--
--
    base_username varchar2(15):='ws';
    lab_password varchar2(20):='xxxxxxxxxx';
    initial_password varchar2(20):='';
    user_count number:=10;  --  1= no number added,create just the base 
end lab_config;
/
```
user_count defines the amount of users created, based on base_username, in the example above,  
ws01- ws10 will be created.  
The create/drop script uses the lab_config PL/SQL package for creation/deletion
Then run the scripts as administrator from Database Actions/SQL Developer.  

[create_user.sql](files/create_user.sql)  
[create_workspace.sql](files/create_workspace.sql)  

When done, delete the users with  
[drop_workspace.sql](files/drop_workspace.sql)  
[drop_users.sql](files/drop_users.sql)  
