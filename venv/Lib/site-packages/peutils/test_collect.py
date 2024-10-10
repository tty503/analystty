from .transutil import *



def test_rectToBbox():
    shape =  {
        "x": 1999.642469,
        "y": 1512.419675,
        "width": 206.982085,
        "height": 65.274763,
        "rotation": 0,
        "points": [
          {
            "x": 1999.642469,
            "y": 1512.419675
          },
          {
            "x": 2206.624554,
            "y": 1512.419675
          },
          {
            "x": 2206.624554,
            "y": 1577.694438
          },
          {
            "x": 1999.642469,
            "y": 1577.694438
          }
        ]
      }
    # print(rectToBbox(shape))
    assert rectToBbox(shape) == (1999.642469, 1512.419675, 206.982085, 65.274763)

    assert rectToBbox(shape, int) == (1999, 1512, 206, 65)

    assert rectToBbox(shape, lambda i: int(round(i,0)) ) == (2000, 1512, 207, 65)

    assert all([isinstance(x,float) for x in rectToBbox(shape,float) ]) ==True

    assert all([isinstance(x,int) for x in rectToBbox(shape,int) ]) ==True




def test_pointsToList():
    points =  [
          {
            "x": 1999.642469,
            "y": 1512.419675
          },
          {
            "x": 2206.624554,
            "y": 1512.419675
          },
          {
            "x": 2206.624554,
            "y": 1577.694438
          },
          {
            "x": 1999.642469,
            "y": 1577.694438
          }
        ]

    assert pointsToList(points) == [[1999.642469, 1512.419675], [2206.624554, 1512.419675], [2206.624554, 1577.694438], [1999.642469, 1577.694438]]
    assert pointsToList(points,adpter=lambda i: int(round(i,0))) == [[2000, 1512], [2207, 1512], [2207, 1578], [2000, 1578]]

