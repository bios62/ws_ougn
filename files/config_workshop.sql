set serveroutput on
create or replace package lab_config as
--
--  Package that configures the PL/SQL creating the workshop
--  Run prior to user creation or workspace creation, set defaults
--  (c) Inge Os 2024
--  08.05.25
--
--
    base_username varchar2(15):='labsomething';
    lab_password varchar2(20):='apassword';
    -- initial_password varchar2(20):='';
    user_count number:=10;  --  1= no number added,create just the base 
end lab_config;
/
