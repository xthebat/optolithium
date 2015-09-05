twiddle_count = 2^14;
line_count = 8;
test_indx = 0;
test_size = 8;

x = (0:twiddle_count-1) * (2*pi) / twiddle_count;
y = sin(x);

imag_indx = length(y)/test_size*test_indx + 1;
real_indx = mod(imag_indx + length(y)/4, length(y));

real_part = y(real_indx);
imag_part = y(imag_indx);

fprintf('Twiddle count = %d\n', twiddle_count);
fprintf('%2d/%2d = %.4f %.4f\n', test_indx, test_size, real_part, imag_part);

return;

out = fopen('twiddle_array.h', 'w');

fprintf(out, '#ifndef TWIDDLE_ARRAY_H_\n');
fprintf(out, '#define TWIDDLE_ARRAY_H_\n');
fprintf(out, '#include <complex.h>\n');
fprintf(out, '#define TWIDDLE_ARRAY_SIZE %d\n', twiddle_count);
fprintf(out, 'static double TWIDDLE_ARRAY[TWIDDLE_ARRAY_SIZE] = {\n');

for k = 1:line_count:length(y),
    fprintf(out, '%.16ff, ', y(k:k+line_count-1));
    fprintf(out, '\n');
end;

fprintf(out, '};\n');
fprintf(out, '#endif /* TWIDDLE_ARRAY_H_ */\n');

fclose(out);