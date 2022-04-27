# Woosh
05/2021-12.04.2022 R.I.P.

Когда-то это был приватный репозиторий с кодом для замечательного бота... 

А что собственно здесь было?
Был бот который позволял манипулировать самокатами Whoosh:
- Бибикать самокатами вокруг точки с радиусом
- Следить за любыми самокатами
- Смотреть скрытую информацию о самокатах


И многое другое


Почему же не работает? Пофиксили(

Скрины былого величия:
<details>
  <summary>Нахождение информации о самокате в данный момент </summary>
  
  ![image](https://user-images.githubusercontent.com/48181730/165542466-dfc13e0d-9928-4b79-a138-7aa14eb8b53f.png)
  После нажатия "MoreInfo"

  ![image](https://user-images.githubusercontent.com/48181730/165548678-65678abd-0449-42e9-891b-1cde7f698987.png)
  
</details>

<details>
  <summary>Слежка за самокатом </summary>
  
  Бот выдавал карту перемещения самоката за последние n секунд в виде html файла.
  ![image](https://user-images.githubusercontent.com/48181730/165602447-57ba0da6-8226-40a3-9f87-6024fe1c667e.png)
  ![image](https://user-images.githubusercontent.com/48181730/165602499-7fcc2aca-e932-4850-9a57-075f8b4f5662.png)
  
</details>
<details>
  <summary>Демонстрация краденых самокатов</summary>
  
  ![image](https://user-images.githubusercontent.com/48181730/165603093-b9d9f73f-2705-40d6-86b7-2eff400ef96e.png)
  ![image](https://user-images.githubusercontent.com/48181730/165603332-36e85cce-1b5a-4f5b-983e-3cf4559052ef.png)

  
  
</details>
<details>
  <summary>Отправка звукового сигнала на множество самокатов в области</summary>
  
  ![image](https://user-images.githubusercontent.com/48181730/165603929-59579d30-4477-4759-97aa-a5b701317a3e.png)
  К сожалению видео с результатами после этой команды не осталось, но есть и другие
  Вот например:

  https://user-images.githubusercontent.com/48181730/165604530-9925fa09-6ff3-416b-a719-00b33421e2c6.mp4


  
</details>
Как работало

![image](https://user-images.githubusercontent.com/48181730/165612067-a6fe8805-7b3e-4dee-9117-3e7eeb6ee5c4.png)

Отслеживание самокатов было возможно благодаря:
1. отсутствию ограничений на количество запросов к API
2. отсутствию ограничений на запрос информации о самокате. (т.е. пользователь мог узнать информацию о самокате по коду, даже если на нём ехал кто-то другой или он был на ремонте/украден/нуждался в зарядке и т.п.)

Вот и всё.
