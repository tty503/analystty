#include <stdio.h> 
#include <windows.h>

#include <stdbool.h>

int newfunc(void)
{
	printf("new 3");
	Sleep(250);
	return 0;
}

void new2(int a)
{
	printf("new 2");
	a = 0x9;
	WinExec("cmd.exe", SW_SHOW);
}

int main(int argc, char** argv)
{
	printf("Principal\n");
	Sleep(1000);
	if(true)
	{
		int a = 0x9323;
		a = a - 1;
		WinExec("cmd.exe", SW_SHOW);
	}
	newfunc();
	new2(0x25);
	return 0;
}