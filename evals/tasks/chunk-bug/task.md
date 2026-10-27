/build Bug: chunk() in app/util.py drops the last partial chunk (chunk([1,2,3], 2) returns [[1, 2]] instead of [[1, 2], [3]]). Fix it and add a regression test.
